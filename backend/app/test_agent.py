"""Observation agent: tool loop over both formats, evidence ledger, reviewer, approvals, budgets and follow-ups."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from app.agent import loop, providers
from app.models import AgentRun, AgentSession, AnalysisRun, ObservationReport
from app.test_observation import ObservationFixture


class Script:
    """A local model endpoint that answers each request with the next scripted reply."""
    def __init__(self):
        self.requests, self.replies = [], []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                outer.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                data = json.dumps(outer.replies.pop(0) if outer.replies else {"error": "script exhausted"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def openai(text="", calls=()):
    message = {"role": "assistant", "content": text or None}
    if calls:
        message["tool_calls"] = [{"id": f"call_{i}_{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
                                 for i, (name, args) in enumerate(calls)]
    return {"model": "m", "choices": [{"message": message, "finish_reason": "tool_calls" if calls else "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


def anthropic(text="", calls=()):
    content = ([{"type": "text", "text": text}] if text else []) + \
        [{"type": "tool_use", "id": f"toolu_{i}", "name": name, "input": args} for i, (name, args) in enumerate(calls)]
    return {"model": "m", "content": content, "stop_reason": "tool_use" if calls else "end_turn", "usage": {"input_tokens": 10, "output_tokens": 5}}


class AgentTests(ObservationFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.script = Script()
        self.addCleanup(self.script.close)
        self.run_fish = self.fish([0, 2, 4])

    def configure(self, api_format="openai_chat"):
        self.client.put("/api/v1/report-agent/config", {"api_format": api_format, "base_url": self.script.url, "model": "m",
                        "api_key": "key-0123456789abcdef", "enabled": True, "timeout_seconds": 5}, content_type="application/json")

    def start(self, text="分析本次观测"):
        response = self.client.post(f"/api/v1/sites/{self.site.pk}/agent-sessions", {"text": text}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def work(self):
        call_command("run_agent_worker", once=True)

    def latest(self):
        return AgentRun.objects.order_by("-created_at").first()

    def test_openai_loop_plans_uses_tools_and_revises_unverified_numbers(self):
        self.configure()
        compute = ("compute_observation_metrics", {"run_ids": [str(self.run_fish.pk)], "observed_on": "2026-11-05"})
        self.script.replies = [
            openai("先制定计划。", [("update_plan", {"steps": [{"title": "了解现状", "status": "in_progress"}, {"title": "计算指标", "status": "pending"}]}),
                                 ("list_videos", {})]),
            openai(calls=[compute]),
            openai("{{S1.v1.label}} 平均可见鱼数为 {{S1.v1.fish.mean_count}}，大约 7 条 [SCHOBERND-2014]。"),
            openai("{{S1.v1.label}} 平均可见鱼数为 {{S1.v1.fish.mean_count}} [SCHOBERND-2014]。"),
        ]
        self.start()
        self.work()
        run = self.latest()
        self.assertEqual(run.status, "completed", run.error_code)
        kinds = list(run.steps.order_by("index").values_list("kind", flat=True))
        self.assertEqual(kinds, ["message", "plan", "tool", "tool", "review", "answer"])
        self.assertEqual(run.plan[0], {"title": "了解现状", "status": "in_progress"})
        self.assertIn({"text": "2.00 尾/帧", "metric": "S1.v1.fish.mean_count"}, run.answer["segments"])
        self.assertIn({"text": "视频 1", "metric": "S1.v1.label"}, run.answer["segments"])
        first, second, third, fourth = self.script.requests
        self.assertEqual({t["function"]["name"] for t in first["tools"]} >= {"update_plan", "propose_observation_report"}, True)
        self.assertEqual(second["messages"][-1]["role"], "tool")
        self.assertEqual(second["messages"][2]["tool_calls"][0]["function"]["name"], "update_plan")
        self.assertIn("没有用占位符：7", fourth["messages"][-1]["content"])
        tool_payload = json.loads(third["messages"][-1]["content"])
        self.assertEqual(tool_payload["metrics_set"], "S1")
        self.assertNotIn("fish.mp4", json.dumps(third))
        self.assertEqual(run.usage["turns"], 4)

    def test_anthropic_report_proposal_waits_for_approval_then_resumes(self):
        self.configure("anthropic_messages")
        narrative = {"summary": "平均可见鱼数为 {{S1.v1.fish.mean_count}} [SCHOBERND-2014]。", "limitations": ["相对丰度指标。"]}
        self.script.replies = [
            anthropic(calls=[("compute_observation_metrics", {"run_ids": [str(self.run_fish.pk)], "observed_on": "2026-11-05"})]),
            anthropic("起草报告。", [("propose_observation_report", {"metrics_set": "S1", "narrative": narrative})]),
            anthropic("报告已保存，{{S1.v1.fish.peak_count}} 为画面峰值。"),
        ]
        session = self.start("出一份报告")
        self.work()
        run = self.latest()
        self.assertEqual(run.status, "awaiting_approval")
        approval = run.steps.get(kind="approval")
        self.assertEqual(approval.payload["proposal"]["narrative"]["summary"][1], {"text": "2.00 尾/帧", "metric": "v1.fish.mean_count"})
        self.assertEqual(ObservationReport.objects.count(), 0)
        decision = self.client.post(f"/api/v1/agent-runs/{run.pk}/decisions", {"tool_call_id": "toolu_0", "decision": "approve"}, content_type="application/json")
        self.assertEqual(decision.status_code, 200)
        report = ObservationReport.objects.get()
        self.assertEqual((report.payload["agent"]["mode"], report.payload["agent"]["agent_run_id"]), ("agent_run", str(run.pk)))
        self.assertIn("平均可见鱼数为 2.00 尾/帧", report.markdown)
        self.assertEqual(self.client.post(f"/api/v1/agent-runs/{run.pk}/decisions", {"tool_call_id": "toolu_0", "decision": "approve"},
                                          content_type="application/json").status_code, 409)
        self.work()
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        resumed = self.script.requests[2]["messages"]
        self.assertEqual([m["role"] for m in resumed], ["user", "assistant", "user", "assistant", "user"])
        self.assertEqual(resumed[-1]["content"][0]["type"], "tool_result")
        self.assertIn(str(report.pk), resumed[-1]["content"][0]["content"])
        self.assertEqual(self.client.get(f"/api/v1/agent-sessions/{session['id']}").json()["runs"][0]["status"], "completed")

    def test_draft_review_rejection_and_follow_up_keep_the_ledger(self):
        self.configure()
        bad = {"summary": "平均 {{S1.v1.fish.nope}} 条。"}
        good = {"summary": "平均可见鱼数为 {{S1.v1.fish.mean_count}}。"}
        self.script.replies = [
            openai(calls=[("compute_observation_metrics", {"run_ids": [str(self.run_fish.pk)]})]),
            openai(calls=[("propose_observation_report", {"metrics_set": "S1", "narrative": bad})]),
            openai(calls=[("propose_observation_report", {"metrics_set": "S1", "narrative": good})]),
            openai("好的，不保存。"),
            openai("峰值是 {{S1.v1.fish.peak_count}}。"),
        ]
        self.start()
        self.work()
        run = self.latest()
        review = run.steps.get(kind="review")
        self.assertEqual(review.payload["audit"]["unknown_metrics"], ["v1.fish.nope"])
        self.assertEqual(run.status, "awaiting_approval")
        self.client.post(f"/api/v1/agent-runs/{run.pk}/decisions", {"tool_call_id": "call_0_propose_observation_report", "decision": "reject", "note": "先别保存"},
                         content_type="application/json")
        self.work()
        run.refresh_from_db()
        self.assertEqual((run.status, ObservationReport.objects.count()), ("completed", 0))
        self.assertIn("先别保存", self.script.requests[3]["messages"][-1]["content"])
        follow = self.client.post(f"/api/v1/agent-sessions/{run.session_id}/messages", {"text": "峰值呢？"}, content_type="application/json")
        self.assertEqual(follow.status_code, 201)
        self.work()
        second = self.latest()
        self.assertEqual(second.status, "completed")
        self.assertIn({"text": "4 尾", "metric": "S1.v1.fish.peak_count"}, second.answer["segments"])
        self.assertEqual(self.script.requests[4]["messages"][-1], {"role": "user", "content": "峰值呢？"})

    def test_tool_errors_budget_cancel_and_guards(self):
        self.configure()
        self.script.replies = [openai(calls=[("drop_tables", {}), ("fish_window_summary", {"run_id": str(self.run_fish.pk), "start_s": 5, "end_s": 1})])] + \
            [openai(calls=[("list_videos", {})]) for _ in range(5)]
        with patch.object(loop, "MAX_TURNS", 3):
            self.start()
            self.work()
        run = self.latest()
        self.assertEqual((run.status, run.error_code), ("failed", "agent_budget_exhausted"))
        errors = json.loads(self.script.requests[1]["messages"][-1]["content"])
        self.assertEqual(errors["error"], "invalid_argument")
        self.assertEqual(json.loads(self.script.requests[1]["messages"][-2]["content"])["error"], "unknown_tool")
        self.assertIn("步骤上限", self.script.requests[3]["messages"][-2]["content"] if self.script.requests[3]["messages"][-1]["role"] == "tool" else self.script.requests[3]["messages"][-1]["content"])
        self.script.replies = [openai(calls=[("propose_analysis_run", {"video_id": self.task.pk, "kind": "coral"})])]
        self.client.post(f"/api/v1/agent-sessions/{run.session_id}/messages", {"text": "补一个珊瑚分析"}, content_type="application/json")
        self.work()
        pending = self.latest()
        self.assertEqual(pending.status, "awaiting_approval")
        self.assertEqual(self.client.post(f"/api/v1/agent-sessions/{run.session_id}/messages", {"text": "再来"}, content_type="application/json").status_code, 409)
        self.assertEqual(self.client.post(f"/api/v1/agent-runs/{pending.pk}/cancel").json()["status"], "cancelled")
        self.assertFalse(AnalysisRun.objects.filter(model=self.coral, status="queued").exists())
        self.client.put("/api/v1/report-agent/config", {"enabled": False}, content_type="application/json")
        self.assertEqual(self.client.post(f"/api/v1/sites/{self.site.pk}/agent-sessions", {"text": "x"}, content_type="application/json").status_code, 409)

    def test_analysis_proposal_and_timeline_numbers(self):
        self.configure()
        self.script.replies = [
            openai(calls=[("fish_activity_timeline", {"run_id": str(self.run_fish.pk), "bin_seconds": 1}), ("propose_analysis_run", {"video_id": self.task.pk, "kind": "coral"})]),
            openai("最活跃时段是 {{T1.busiest.window}}，平均 {{T1.busiest.mean_count}}。"),
        ]
        self.start()
        self.work()
        run = self.latest()
        timeline = {k: v["value"] for k, v in run.ledger["metrics"].items() if k.startswith("T1.b")}
        self.assertEqual([timeline[f"T1.b0{i}.mean_count"] for i in range(3)], [0, 2, 4])
        self.client.post(f"/api/v1/agent-runs/{run.pk}/decisions", {"tool_call_id": "call_1_propose_analysis_run", "decision": "approve"}, content_type="application/json")
        queued = AnalysisRun.objects.get(model=self.coral)
        self.assertEqual((queued.status, queued.task_id), ("queued", self.task.pk))
        self.work()
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        tools = [m for m in self.script.requests[1]["messages"] if m["role"] == "tool"]
        self.assertEqual([m["tool_call_id"] for m in tools], ["call_0_fish_activity_timeline", "call_1_propose_analysis_run"])
        self.assertIn({"text": "2–3 s", "metric": "T1.busiest.window"}, run.answer["segments"])
        polled = self.client.get(f"/api/v1/agent-runs/{run.pk}", {"after": 2}).json()
        self.assertTrue(all(step["index"] > 2 for step in polled["steps"]))

    def test_markdown_list_numbering_is_not_audited_as_data(self):
        ctx = loop.Context(AgentRun(session=AgentSession(site=self.site)))
        ctx.metrics["S1.m"] = {"display": "2.00 尾/帧", "label": "平均"}
        parts, audit = loop.audit_text(ctx, "## 结论\n1. 平均 {{S1.m}}\n  2) 峰值 7 条\n- 第 2 段")
        self.assertEqual(audit["unverified_numbers"], ["2", "7"])
        self.assertIn({"text": "1."}, parts)
        self.assertIn({"text": "2)"}, parts)

    def test_anthropic_transcript_alternates_roles(self):
        transcript = [{"role": "user", "text": "a"}, {"role": "assistant", "text": "", "tool_calls": [{"id": "t1", "name": "x", "arguments": {}}]},
                      {"role": "tool", "tool_call_id": "t1", "name": "x", "content": "{}", "is_error": False}, {"role": "user", "text": "[平台审计] …"}]
        messages = providers.anthropic_messages(transcript)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user"])
        self.assertEqual([b["type"] for b in messages[2]["content"]], ["tool_result", "text"])

    # Sessions started from a video on the monitoring wall carry what the observer is looking at.
    def test_wall_session_reads_the_current_frame_and_offers_seekable_times(self):
        self.configure()
        coral = self.coral_run([(50, 40, 10), (60, 40, 0), (50, 25, 25)])
        self.script.replies = [
            openai(calls=[("get_playback_context", {}), ("fish_activity_timeline", {"run_id": str(self.run_fish.pk), "bin_seconds": 1})]),
            openai("{{V%d.label}} 在 {{P1.time}} 可见 {{P1.fish.visible_now}}，最活跃在 {{T1.busiest.window}}。" % self.task.pk),
        ]
        context = {"current_time_s": 1.2, "fish_run_id": str(self.run_fish.pk), "coral_run_id": str(coral.pk)}
        response = self.client.post(f"/api/v1/tasks/{self.task.pk}/agent-sessions", {"text": "现在画面里鱼多吗？", "context": context}, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["task_id"], response.json()["site_id"]), (self.task.pk, None))
        self.work()
        run = self.latest()
        self.assertEqual(run.status, "completed", run.error_code)
        self.assertEqual(run.context, {"task_id": self.task.pk, "current_time_s": 1.2, "fish_run_id": str(self.run_fish.pk), "coral_run_id": str(coral.pk)})
        system = self.script.requests[0]["messages"][0]["content"]
        self.assertIn("监测大屏", system)
        self.assertIn(str(self.run_fish.pk), system)
        self.assertNotIn(self.task.original_filename, json.dumps(self.script.requests, ensure_ascii=False))
        ledger = run.ledger["metrics"]
        self.assertEqual((ledger["P1.time"]["seek_s"], ledger["P1.fish.visible_now"]["value"]), (1.2, 2))
        self.assertEqual((ledger["P1.coral.sample_time"]["value"], ledger["P1.coral.bleached_fraction"]["value"]), (1.0, 0.0))
        self.assertEqual((ledger["T1.busiest.window"]["seek_s"], ledger["T1.busiest.window"]["task_id"]), (2, self.task.pk))
        self.assertIn({"text": self.task.original_filename, "metric": f"V{self.task.pk}.label"}, run.answer["segments"])
        self.assertFalse(run.answer["audit"]["unknown_metrics"])

    def test_wall_session_needs_a_site_to_save_a_report(self):
        self.configure()
        self.script.replies = [
            openai(calls=[("compute_observation_metrics", {"run_ids": [str(self.run_fish.pk)]})]),
            openai(calls=[("get_site_overview", {}), ("propose_observation_report", {"metrics_set": "S1", "narrative": {"summary": "{{S1.v1.fish.mean_count}}"}})]),
            openai("需要先选择观测点。"),
        ]
        created = self.client.post(f"/api/v1/tasks/{self.task.pk}/agent-sessions", {"text": "出报告"}, content_type="application/json").json()
        self.work()
        run = self.latest()
        self.assertEqual(run.status, "completed")
        results = [json.loads(m["content"]) for m in self.script.requests[2]["messages"] if m["role"] == "tool"]
        self.assertEqual([r.get("error") for r in results], [None, "no_site", "no_site"])
        self.assertEqual(run.ledger["metrics"]["S1.site.name"]["value"], "未归档")
        filed = self.client.patch(f"/api/v1/agent-sessions/{created['id']}", {"site_id": str(self.site.pk)}, content_type="application/json")
        self.assertEqual(filed.json()["site_name"], self.site.name)
        site_session = self.start()
        self.assertEqual(self.client.patch(f"/api/v1/agent-sessions/{site_session['id']}", {"site_id": None}, content_type="application/json").status_code, 409)

    def test_wall_context_is_validated(self):
        self.configure()
        url = f"/api/v1/tasks/{self.task.pk}/agent-sessions"
        for context in ({"current_time_s": -1}, {"current_time_s": "1"}, {"secret": 1}, {"fish_run_id": "x"}):
            self.assertEqual(self.client.post(url, {"text": "x", "context": context}, content_type="application/json").json()["error"]["code"], "invalid_context")
        self.assertEqual(self.client.post(url, {"text": "x", "site_id": "nope"}, content_type="application/json").json()["error"]["code"], "unknown_site")
        foreign = self.client.post(url, {"text": "x", "context": {"current_time_s": 3, "coral_run_id": str(self.run_fish.pk)}}, content_type="application/json").json()
        self.assertEqual(foreign["runs"][0]["context"], {"task_id": self.task.pk, "current_time_s": 3.0})
        self.assertEqual(len(self.client.get(url).json()["items"]), 1)
