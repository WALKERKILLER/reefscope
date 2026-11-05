"""Observation facts, CRW alert levels, write-only agent keys, both API formats and audited narratives."""
import datetime
import json
import stat
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from app.analysis.storage import attempt_directory, write_json
from app.models import AnalysisRun, ModelVersion, ObservationReport, ObservationSite
from app.observation import agent, facts
from app.test_analysis import RunFixture


class Upstream:
    """A local HTTP endpoint that records requests and replies with a scripted response."""
    def __init__(self):
        self.requests, self.reply = [], (200, {})
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
                status, payload = outer.reply
                self.send_response(status)
                if status in (301, 302):
                    self.send_header("Location", "http://127.0.0.1:9/elsewhere")
                data = json.dumps(payload).encode()
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


class ObservationFixture(RunFixture):
    def setUp(self):
        super().setUp()
        self.keys = override_settings(REPORT_AGENT_KEY_PATH=self.root / "secrets" / "agent.key")
        self.keys.enable()
        self.addCleanup(self.keys.disable)
        self.coral = ModelVersion.objects.create(id="coral:test", kind="coral", weight_path="private.safetensors", sha256="b" * 64,
                                                 labels={"0": "background", "1": "non_bleached", "2": "bleached"}, framework_version="test")
        self.site = ObservationSite.objects.create(name="北礁 A", latitude=16.5, longitude=111.6, depth_m=6)

    def completed(self, model, settings, summary, name, lines):
        run = AnalysisRun.objects.create(task=self.task, model=model, status="completed", attempt=1, attempt_token=uuid.uuid4(), summary=summary,
                                         config_snapshot={"models": {model.kind: model.pk}, "model_sha256": model.sha256, "settings": settings})
        folder = attempt_directory(run)
        (folder / name).write_text("".join(json.dumps(line) + "\n" for line in lines))
        write_json(folder / "summary.json", summary)
        return run

    def fish(self, per_frame, motion="unknown"):
        """`per_frame[i]` fish in frame i, each its own track that lasts the whole clip."""
        lines = [{"schema": "fish-tracks/v1", "track_id": track, "frame": frame, "timestamp_ms": frame * 1000.0, "class_id": 0, "label": "fish",
                  "confidence": 0.5, "bbox_xywhn": [0.5, 0.5, 0.1, 0.1], "center_xyn": [0.5, 0.5], "observed": True}
                 for frame, count in enumerate(per_frame) for track in range(1, count + 1)]
        settings = {"confidence_threshold": 0.25, "iou_threshold": 0.45, "tracking_frame_stride": 1, "imgsz": 640,
                    "allowed_gap_seconds": 2.0, "camera_motion": motion, "scene_cut_frames": []}
        return self.completed(self.model, settings, {"frame_count": len(per_frame), "fps": 1.0, "width": 10, "height": 10}, "tracks.jsonl", lines)

    def coral_run(self, counts, motion="unknown"):
        lines = [{"schema": "coral-frames/v1", "frame": i, "timestamp_ms": i * 1000.0, "width": 10, "height": 10, "background_separated": True,
                  "guard_score": 0.1, "pixel_counts": dict(zip("012", row)), "mask": f"masks/{i:08d}.png", "mask_sha256": "0" * 64}
                 for i, row in enumerate(counts)]
        return self.completed(self.coral, {"sample_every_seconds": 1, "camera_motion": motion},
                              {"frame_count": len(counts), "fps": 1.0, "width": 10, "height": 10}, "frames.jsonl", lines)

    def build(self, *runs, environment=None, on=datetime.date(2026, 11, 5)):
        return facts.build(self.site, on, list(runs), facts.validate_environment(environment))


class FactsTests(ObservationFixture, TestCase):
    def test_teaching_example_mean_count_peak_and_presence(self):
        m = self.build(self.fish([0, 2, 4]))["metrics"]
        self.assertEqual(m["v1.fish.mean_count"]["value"], 2)
        self.assertEqual((m["v1.fish.mean_count"]["numerator"], m["v1.fish.mean_count"]["denominator"]), (6, 3))
        self.assertEqual(m["v1.fish.peak_count"]["value"], 4)
        self.assertEqual(m["v1.fish.peak_time"]["value"], 2)
        self.assertAlmostEqual(m["v1.fish.occupied_fraction"]["value"], 2 / 3)
        self.assertEqual(m["v1.fish.ap50"]["status"], "unavailable")

    def test_frames_without_fish_are_zero_not_missing(self):
        m = self.build(self.fish([0, 0]))["metrics"]
        self.assertEqual((m["v1.fish.mean_count"]["value"], m["v1.fish.peak_count"]["value"]), (0, 0))
        self.assertIsNone(m["v1.fish.peak_time"]["value"])

    def test_half_bleached_displays_fifty_percent_and_pools_raw_pixels(self):
        first, second = self.coral_run([(50, 25, 25)]), self.coral_run([(90, 10, 0)])
        m = self.build(first)["metrics"]
        self.assertEqual(m["v1.coral.bleached_coral_fraction"]["value"], 0.5)
        self.assertEqual(m["v1.coral.bleached_coral_fraction"]["display"], "50.0%")
        self.assertEqual(m["v1.coral.cover"]["reason"], "requires_approved_benthic_roi")
        with self.assertRaisesRegex(ValueError, "duplicate_run_kind_for_video"):
            self.build(first, second)
        second.task = type(self.task).objects.create(original_filename="b.mp4", uploaded_video_path="/media/uploads/b.mp4")
        second.save()
        pooled = self.build(first, second)["metrics"]
        self.assertEqual(pooled["site.coral.bleached_coral_fraction"]["value"], 25 / 60)
        self.assertEqual(pooled["site.coral.coral_pixel_share"]["value"], 60 / 200)

    def test_crw_bleaching_alert_area_boundaries(self):
        cases = [((-0.1, None), "no_stress"), ((0, 30), "no_stress"), ((0.5, None), "watch"), ((1, None), None), ((1, 0), None),
                 ((1, 3.9), "warning"), ((1, 4), "alert_1"), ((1.5, 8), "alert_2"), ((1, 12), "alert_3"), ((1, 19.9), "alert_4"), ((1, 20), "alert_5")]
        for (hotspot, dhw), expected in cases:
            self.assertEqual(facts.alert_area(hotspot, dhw)[0], expected, (hotspot, dhw))
        self.assertEqual(facts.alert_area(1, 0)[1], "inconsistent_hotspot_and_dhw")
        self.assertEqual(facts.alert_area(None, 9)[1], "missing_hotspot")
        for bad in ({"dhw_c_weeks": -1}, {"hotspot_c": float("nan")}, {"sst_c": True}, {"wind": 1}, {"product_date": "11/05"}):
            with self.assertRaises(ValueError):
                facts.validate_environment(bad)
        self.assertIsNone(facts.validate_environment({"source": "only text"}))

    def test_comparison_requires_same_models_settings_and_fixed_camera(self):
        def report(run, on):
            built = facts.build(self.site, on, [run], None)
            from app.observation import report as render
            payload, markdown, html = render.make(built, {"status": "disabled"})
            ObservationReport.objects.create(site=self.site, observed_on=on, payload=payload, markdown=markdown, html=html)
            return built
        report(self.fish([1, 1], motion="fixed"), datetime.date(2026, 10, 1))
        later = report(self.fish([3, 3], motion="fixed"), datetime.date(2026, 11, 1))
        self.assertTrue(later["comparison"]["comparable"])
        self.assertEqual(later["metrics"]["delta.site.fish.mean_count"]["value"], 2)
        moving = facts.build(self.site, datetime.date(2026, 12, 1), [self.fish([3, 3])], None)
        self.assertEqual(moving["comparison"]["reasons"], ["camera_motion_not_fixed"])
        self.assertNotIn("delta.site.fish.mean_count", moving["metrics"])
        self.assertEqual(moving["metrics"]["prev.site.fish.mean_count"]["value"], 3)


class AgentConfigTests(ObservationFixture, TestCase):
    url = "/api/v1/report-agent/config"

    def put(self, body):
        return self.client.put(self.url, body, content_type="application/json")

    def test_key_is_write_only_owner_only_and_bound_to_base_url(self):
        response = self.put({"base_url": "https://llm.example/v1/", "model": "m-1", "api_key": "sk-test-0123456789abcd", "enabled": True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("sk-test", json.dumps(body))
        self.assertEqual((body["key_configured"], body["key_hint"], body["endpoint"]), (True, "abcd", "https://llm.example/v1/chat/completions"))
        path = self.root / "secrets" / "agent.key"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn("sk-test", json.dumps(self.client.get(self.url).json()))
        moved = self.put({"base_url": "https://other.example", "enabled": False}).json()
        self.assertFalse(moved["key_configured"])
        self.assertFalse(path.exists())
        self.assertEqual(self.put({"enabled": True}).json()["error"]["code"], "agent_config_incomplete")

    def test_rejects_unsafe_urls_keys_and_values(self):
        for body, code in [({"base_url": "ftp://x.example"}, "invalid_base_url"), ({"base_url": "https://u:p@x.example"}, "invalid_base_url"),
                           ({"base_url": "https://x.example/v1?k=1"}, "invalid_base_url"), ({"api_key": "sk-abc\r\nX-Evil: 1"}, "invalid_api_key"),
                           ({"api_format": "gemini"}, "invalid_api_format"), ({"timeout_seconds": 600}, "invalid_timeout"),
                           ({"model": "bad model"}, "invalid_model"), ({"secret": 1}, "invalid_agent_config")]:
            self.assertEqual(self.put(body).json()["error"]["code"], code, body)

    def test_anthropic_endpoint_resolution(self):
        for base, expected in [("https://api.example", "https://api.example/v1/messages"), ("https://api.example/v1", "https://api.example/v1/messages"),
                               ("https://api.example/v1/messages", "https://api.example/v1/messages")]:
            self.assertEqual(agent.endpoint("anthropic_messages", base), expected)


NARRATIVE = {"summary": "{{v1.label}} 的平均可见鱼数为 {{v1.fish.mean_count}} [SCHOBERND-2014]。",
             "observations": ["峰值 {{v1.fish.peak_count}}，另有约 7 条未核对 [FAKE-1]。", "{{v1.fish.unknown}}"],
             "interpretation": [], "limitations": ["像素占比不是覆盖率 [GCRMN-2020]。"], "next_steps": []}


class ReportFlowTests(ObservationFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.upstream = Upstream()
        self.addCleanup(self.upstream.close)
        self.run = self.fish([0, 2, 4])
        self.task.original_filename = "private-name.mp4"
        self.task.save()

    def configure(self, api_format):
        response = self.client.put("/api/v1/report-agent/config", {"api_format": api_format, "base_url": self.upstream.url, "model": "test-model",
                                   "api_key": "key-0123456789abcdef", "enabled": True, "timeout_seconds": 5}, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def create(self, use_agent=True, **extra):
        body = {"site_id": str(self.site.pk), "observed_on": "2026-11-05", "run_ids": [str(self.run.pk)], "use_agent": use_agent} | extra
        return self.client.post("/api/v1/observation-reports", body, content_type="application/json")

    def test_openai_format_request_and_audited_narrative(self):
        self.configure("openai_chat")
        self.upstream.reply = (200, {"model": "test-model", "choices": [{"message": {"content": json.dumps(NARRATIVE, ensure_ascii=False)},
                                                                         "finish_reason": "stop"}], "usage": {"prompt_tokens": 9, "completion_tokens": 3}})
        response = self.create()
        self.assertEqual(response.status_code, 201)
        sent = self.upstream.requests[0]
        self.assertEqual(sent["path"], "/chat/completions")
        self.assertEqual(sent["headers"]["authorization"], "Bearer key-0123456789abcdef")
        self.assertNotIn("max_tokens", sent["body"])
        self.assertNotIn("temperature", sent["body"])
        prompt = sent["body"]["messages"][1]["content"]
        for private in ("private-name", "16.5", "111.6", str(self.run.pk)):
            self.assertNotIn(private, prompt)
        record = response.json()["agent"]
        self.assertEqual(record["status"], "generated")
        self.assertEqual(record["audit"]["unknown_metrics"], ["v1.fish.unknown"])
        self.assertEqual(record["audit"]["unknown_citations"], ["FAKE-1"])
        self.assertEqual(record["audit"]["unverified_numbers"], ["7"])
        self.assertIn({"text": "2.00 尾/帧", "metric": "v1.fish.mean_count"}, record["narrative"]["summary"])
        report = ObservationReport.objects.get()
        self.assertIn("约 7（未核对） 条未核对。", report.markdown)
        self.assertIn("视频 1 的平均可见鱼数为 2.00 尾/帧 [SCHOBERND-2014]", report.markdown)
        self.assertEqual(report.payload["human_review_status"], "pending")
        with self.assertRaises(ValidationError):
            report.save()
        export = self.client.get(f"/api/v1/observation-reports/{report.pk}/export", {"export": "html"})
        self.assertIn("default-src 'none'", export["Content-Security-Policy"])

    def test_anthropic_format_headers_and_token_limit(self):
        self.configure("anthropic_messages")
        self.upstream.reply = (200, {"model": "test-model", "content": [{"type": "text", "text": json.dumps(NARRATIVE)}], "stop_reason": "end_turn",
                                     "usage": {"input_tokens": 9, "output_tokens": 3}})
        self.assertEqual(self.create().json()["agent"]["status"], "generated")
        sent = self.upstream.requests[0]
        self.assertEqual(sent["path"], "/v1/messages")
        self.assertEqual((sent["headers"]["x-api-key"], sent["headers"]["anthropic-version"]), ("key-0123456789abcdef", "2023-06-01"))
        self.assertEqual(sent["body"]["max_tokens"], 4096)
        self.assertIn("{{", sent["body"]["system"])

    def test_failures_still_store_the_deterministic_report(self):
        self.configure("openai_chat")
        for reply, code in [((500, {}), "agent_upstream_error"), ((302, {}), "agent_redirect_refused"), ((401, {}), "agent_auth_failed"),
                            ((200, {"choices": [{"message": {"content": "not json"}}]}), "agent_invalid_response"),
                            ((200, {"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]}), "agent_output_truncated")]:
            self.upstream.reply = reply
            body = self.create().json()
            self.assertEqual((body["agent"]["status"], body["agent"]["error_code"]), ("failed", code))
            self.assertIn("平均可见鱼数", body["sections"][1]["rows"][0][0])
        self.upstream.reply = (401, {})
        self.assertEqual(self.client.post("/api/v1/report-agent/test").json()["error_code"], "agent_auth_failed")
        self.upstream.reply = (200, {"choices": [{"message": {"content": "OK"}}]})
        self.assertTrue(self.client.post("/api/v1/report-agent/test").json()["ok"])

    def test_request_validation_disabled_agent_and_site_protection(self):
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(self.create(use_agent=False).json()["agent"]["status"], "disabled")
        self.assertEqual(self.upstream.requests, [])
        self.assertEqual(self.create(run_ids=[]).status_code, 400)
        self.assertEqual(self.create(run_ids=[str(uuid.uuid4())]).status_code, 404)
        self.assertEqual(self.create(environment={"dhw_c_weeks": "9"}).json()["error"]["code"], "invalid_dhw_c_weeks")
        AnalysisRun.objects.filter(pk=self.run.pk).update(status="running")
        self.assertEqual(self.create(use_agent=False).json()["error"]["code"], "run_not_completed")
        self.assertEqual(self.client.delete(f"/api/v1/sites/{self.site.pk}").json()["error"]["code"], "site_has_reports")
        duplicate = self.client.post("/api/v1/sites", {"name": "北礁 A"}, content_type="application/json")
        self.assertEqual(duplicate.json()["error"]["code"], "site_name_taken")
        listed = self.client.get(f"/api/v1/sites/{self.site.pk}/reports").json()["items"]
        self.assertEqual((len(listed), listed[0]["mean_count"]), (1, "2.00 尾/帧"))
