"""The observation agent loop: plan → call tools → reflect, with approval gates and a deterministic reviewer.

A run executes inside `run_agent_worker`. It pauses with status `awaiting_approval` when the model
proposes an action; a decision through the API re-queues it, and the worker resumes from the stored
transcript. Budgets bound model turns, tool calls and wall time.
"""
import json
import time
import urllib.parse
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from app.models import AgentRun, AgentStep, Task
from app.observation.agent import ERRORS, AgentError, config as agent_config, segments
from app.observation.sources import SOURCES
from . import providers
from .tools import TOOLS, Context, ToolError, definitions, register_video

PROMPT_VERSION = "reefscope-observation-agent/v2"
MAX_TURNS = 14
MAX_TOOL_CALLS = 24
MAX_REVISIONS = 2
MAX_SECONDS = 300
MAX_RESULT_CHARS = 8000
LEASE_SECONDS = 180

SYSTEM = """你是 ReefScope 平台中的珊瑚礁观测分析 Agent，帮助研究人员分析观测点「{site}」的视频结果。今天是 {today}。

工作方式：
1. 先调用 update_plan 列出计划；推进或调整时再次调用，保持清单与实际一致。
2. 用工具取证，不凭记忆回答。先用 list_videos、get_site_overview 了解现状，再用 compute_observation_metrics 计算指标；需要细节时用时间线、时间窗、采样帧复核等工具深入。
3. 每次拿到工具结果后判断：证据是否足够、是否需要换个角度、是否需要向用户确认。用户的要求不明确或缺少必要信息（如环境数据）时，在最终回答中直接提问。
4. 改变平台数据的操作（排队分析、保存报告）只能通过 propose_ 工具提议，由用户批准。用户只要求分析时，不要主动保存报告；用户要求出报告时，用 propose_observation_report 提交草稿。
5. 最终回答用简体中文，先给结论，再列依据和限制，简洁。最终回答可以用 Markdown（小标题、列表、加粗、表格），有序列表的编号不算数值；报告草稿的 narrative 写纯文本，不用 Markdown。

数值与引用：
- 正文中的数值只能写工具返回的指标 ID 占位符，例如 {{{{S1.v1.fish.mean_count}}}}、{{{{T1.busiest.window}}}}；平台会替换成核对过的数值。不要直接写阿拉伯数字，视频用 {{{{V7.label}}}} 或 {{{{S1.v1.label}}}} 指代。
- 只引用 search_references 或资料卡中的 ID，写成 [CRW-BAA]。
- 平台会审计你的回答和报告草稿：出现未知 ID、未知引用或裸数字时会退回，请按提示改写。

解释边界：
- 珊瑚像素占比是画面统计，不是活珊瑚覆盖率；白化像素比例不是群体白化发生率。
- 平均可见鱼数和画面峰值是相对丰度指标；追踪 ID 数不等于个体数。
- 单次观测不能推断趋势或原因；鱼类与珊瑚同时出现不代表因果；不可比的两次观测不描述变化方向。
- 环境数据只作背景；没有独立真值时不评价模型精度；不给健康等级或评分。

可用资料卡：{sources}"""

WALL = """

监测大屏：用户正在大屏上观看视频 #{task}，指代它时用 {{{{{label}}}}}。可直接使用的已完成 Run：{runs}。
- 用户问“现在”“这里”“当前画面”时，先调用 get_playback_context，再按需要看前后时段。
- 提到时刻或时段时使用带时间的指标 ID（如 {{{{T1.busiest.window}}}}、{{{{C1.bleached1.time}}}}、{{{{P1.time}}}}），用户可以点击它跳到视频的这一刻。
- 回答要短，先给结论，适合观测员一边看画面一边读。"""


class Stop(Exception):
    """Ends the current execution segment with a final status."""
    def __init__(self, status, code=""):
        super().__init__(status)
        self.status, self.code = status, code


# --- queue ---

def expire():
    AgentRun.objects.filter(status="running", lease_expires_at__lte=timezone.now()).update(status="failed", error_code="worker_lease_expired")


def claim():
    expire()
    for run_id in AgentRun.objects.filter(status="queued").order_by("created_at").values_list("id", flat=True)[:16]:
        token, now = uuid4(), timezone.now()
        if AgentRun.objects.filter(pk=run_id, status="queued").update(status="running", attempt_token=token,
                                                                         lease_expires_at=now + timedelta(seconds=LEASE_SECONDS), updated_at=now):
            return AgentRun.objects.select_related("session__site").get(pk=run_id)
    return None


def heartbeat(run):
    now = timezone.now()
    if not AgentRun.objects.filter(pk=run.pk, status="running", attempt_token=run.attempt_token).update(lease_expires_at=now + timedelta(seconds=LEASE_SECONDS)):
        raise Stop("lost")
    if AgentRun.objects.filter(pk=run.pk, cancel_requested=True).exists():
        raise Stop("cancelled", "cancelled_by_user")


# --- steps ---

def add_step(run, kind, title, status="done", payload=None, duration_ms=None):
    index = (run.steps.order_by("-index").values_list("index", flat=True).first() or 0) + 1
    return AgentStep.objects.create(run=run, index=index, kind=kind, title=title[:200], status=status, payload=payload or {}, duration_ms=duration_ms)


def save(run, ctx, **fields):
    run.ledger = ctx.dump()
    for key, value in fields.items():
        setattr(run, key, value)
    AgentRun.objects.filter(pk=run.pk).update(transcript=run.transcript, ledger=run.ledger, plan=run.plan, pending=run.pending, answer=run.answer,
                                              usage=run.usage, agent=run.agent, status=run.status, error_code=run.error_code, updated_at=timezone.now())


def compact(result):
    text = json.dumps(result, ensure_ascii=False, allow_nan=False, default=str)
    return text if len(text) <= MAX_RESULT_CHARS else text[:MAX_RESULT_CHARS] + "…（结果过长已截断，请缩小范围）"


def tool_message(call, result, is_error=False):
    return {"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": compact(result), "is_error": is_error}


def render_metrics(ctx):
    """Final answers show the user-facing label (for example the file name) where a tool supplied one."""
    return {name: item | {"display": item.get("user_display") or item["display"]} for name, item in ctx.metrics.items()}


def audit_text(ctx, text):
    audit = {"unverified_numbers": [], "unknown_metrics": [], "unknown_citations": [], "citations": []}
    parts = segments(text, render_metrics(ctx), audit)
    return parts, {key: sorted(set(values)) for key, values in audit.items()}


def review_feedback(audit, what):
    problems = []
    if audit["unknown_metrics"]:
        problems.append("这些指标 ID 不存在：" + "、".join(audit["unknown_metrics"]))
    if audit["unknown_citations"]:
        problems.append("这些资料 ID 不存在：" + "、".join(audit["unknown_citations"]))
    if audit["unverified_numbers"]:
        problems.append("这些数字没有用占位符：" + "、".join(audit["unverified_numbers"][:8]))
    return f"[平台审计] {what}未通过：" + "；".join(problems) + "。请只用工具返回的指标 ID 和资料 ID 改写，必要时先调用工具取得指标。"


def failed_review(audit):
    return bool(audit["unknown_metrics"] or audit["unknown_citations"] or audit["unverified_numbers"])


# --- execution ---

def run_tool(run, ctx, call, budget):
    """Executes a read tool or prepares an action proposal. Returns (message or None, proposal or None)."""
    tool = TOOLS.get(call["name"])
    started = time.monotonic()
    if tool is None or call.get("problem"):
        code = "unknown_tool" if tool is None else call["problem"]
        add_step(run, "tool", f"调用 {call['name']}", "error", {"tool": call["name"], "arguments": call["arguments"], "error": code})
        return tool_message(call, {"error": code}, True), None
    budget["tool_calls"] += 1
    try:
        if tool["kind"] == "read":
            result, ids, summary = tool["handler"](ctx, call["arguments"])
            kind = "plan" if call["name"] == "update_plan" else "tool"
            add_step(run, kind, tool["title"], "done", {"tool": call["name"], "arguments": call["arguments"], "summary": summary,
                                                         "metric_ids": ids[:200], "plan": run.plan if kind == "plan" else None},
                     round((time.monotonic() - started) * 1000))
            return tool_message(call, result), None
        proposal = tool["prepare"](ctx, call["arguments"])
    except ToolError as exc:
        add_step(run, "tool", tool["title"], "error", {"tool": call["name"], "arguments": call["arguments"], "error": exc.code, "detail": exc.detail},
                 round((time.monotonic() - started) * 1000))
        return tool_message(call, {"error": exc.code, "detail": exc.detail}, True), None
    if call["name"] == "propose_observation_report" and failed_review(proposal["audit"]) and budget["revisions"] < MAX_REVISIONS:
        budget["revisions"] += 1
        feedback = review_feedback(proposal["audit"], "报告草稿")
        add_step(run, "review", "审计报告草稿：退回改写", "warning", {"audit": proposal["audit"], "round": budget["revisions"]})
        return tool_message(call, {"error": "review_failed", "detail": feedback}, True), None
    step = add_step(run, "approval", tool["title"], "pending", {"tool": call["name"], "tool_call_id": call["id"], "proposal": proposal})
    return None, {"tool_call_id": call["id"], "step": step.index, "tool": call["name"], "proposal": proposal, "decision": None, "result": None}


def resume_pending(run):
    """After every proposal is decided, append all tool results of that turn in call order."""
    pending = run.pending
    for call in pending["calls"]:
        result = pending["results"].get(call["id"])
        decided = next((p for p in pending["proposals"] if p["tool_call_id"] == call["id"]), None)
        if decided:
            result = decided["result"]
        run.transcript.append(result)
    run.pending = {}


def system_prompt(run, ctx):
    text = SYSTEM.format(site=ctx.site.name if ctx.site else "（未归档）", today=timezone.localdate().isoformat(), sources="、".join(SOURCES))
    context = run.context or {}
    if context.get("task_id"):
        runs = "；".join(f"{label} {context[key]}" for key, label in (("fish_run_id", "鱼类"), ("coral_run_id", "珊瑚")) if context.get(key)) or "无，先用 list_videos 查看"
        text += WALL.format(task=context["task_id"], label=f"V{context['task_id']}.label", runs=runs)
    return text


def execute(run):
    ctx = Context(run)
    config = agent_config()
    if not config.enabled:
        raise Stop("failed", "agent_disabled")
    run.agent = run.agent or {"prompt_version": PROMPT_VERSION, "api_format": config.api_format, "model": config.model,
                              "host": urllib.parse.urlsplit(config.base_url).hostname or ""}
    task = Task.objects.filter(pk=(run.context or {}).get("task_id")).first() if (run.context or {}).get("task_id") else None
    if task is not None:
        register_video(ctx, task)
    if run.pending:
        resume_pending(run)
        add_step(run, "resume", "继续执行")
    run.usage = usage = run.usage or {"input_tokens": 0, "output_tokens": 0, "turns": 0, "tool_calls": 0, "revisions": 0}
    budget = {"tool_calls": usage["tool_calls"], "revisions": usage["revisions"]}
    started = time.monotonic()
    system = system_prompt(run, ctx)
    tools = definitions()
    while True:
        heartbeat(run)
        if usage["turns"] >= MAX_TURNS or budget["tool_calls"] >= MAX_TOOL_CALLS or time.monotonic() - started > MAX_SECONDS:
            if usage.get("wrap_up"):
                raise Stop("failed", "agent_budget_exhausted")
            usage["wrap_up"] = True
            run.transcript.append({"role": "user", "text": "[平台] 已达到本次任务的步骤上限。请不再调用工具，基于已有证据给出最终回答，并说明还缺什么。"})
            add_step(run, "review", "达到步骤上限，要求收尾", "warning")
        turn_started = time.monotonic()
        try:
            reply = providers.turn(config, system, run.transcript, tools)
        except AgentError as exc:
            add_step(run, "error", "调用模型服务失败", "error", {"error": exc.code, "error_text": ERRORS.get(exc.code), "http_status": exc.http_status})
            raise Stop("failed", exc.code)
        usage["turns"] += 1
        for key in ("input_tokens", "output_tokens"):
            usage[key] += reply["usage"].get(key) or 0
        calls = reply["tool_calls"]
        run.transcript.append({"role": "assistant", "text": reply["text"], "tool_calls": [{k: c[k] for k in ("id", "name", "arguments")} for c in calls]})
        elapsed = round((time.monotonic() - turn_started) * 1000)
        if not calls:
            if reply["stop"] == "max_tokens":
                add_step(run, "error", "输出达到长度上限", "error", {"error": "agent_output_truncated"})
                raise Stop("failed", "agent_output_truncated")
            parts, audit = audit_text(ctx, reply["text"])
            if failed_review(audit) and budget["revisions"] < MAX_REVISIONS:
                budget["revisions"] += 1
                add_step(run, "review", "审计最终回答：退回改写", "warning", {"audit": audit, "round": budget["revisions"]}, elapsed)
                run.transcript.append({"role": "user", "text": review_feedback(audit, "最终回答")})
                usage.update(tool_calls=budget["tool_calls"], revisions=budget["revisions"])
                save(run, ctx, usage=usage)
                continue
            add_step(run, "answer", "回答", "done", {"segments": parts, "audit": audit}, elapsed)
            usage.update(tool_calls=budget["tool_calls"], revisions=budget["revisions"])
            run.answer = {"segments": parts, "audit": audit}
            save(run, ctx, usage=usage, status="completed")
            return
        if reply["text"]:
            add_step(run, "message", "说明", "done", {"text": reply["text"]}, elapsed)
        results, proposals = {}, []
        for call in calls:
            message, proposal = run_tool(run, ctx, call, budget)
            if proposal:
                proposals.append(proposal)
            else:
                results[call["id"]] = message
        usage.update(tool_calls=budget["tool_calls"], revisions=budget["revisions"])
        if proposals:
            run.pending = {"calls": [{"id": c["id"], "name": c["name"]} for c in calls], "results": results, "proposals": proposals}
            save(run, ctx, usage=usage, status="awaiting_approval")
            return
        run.transcript.extend(results[c["id"]] for c in calls)
        save(run, ctx, usage=usage)


def process(run):
    """Worker entry point: runs one execution segment and records the terminal state."""
    try:
        execute(run)
    except Stop as stop:
        if stop.status == "lost":
            return
        if stop.status == "cancelled":
            add_step(run, "error", "已停止", "cancelled", {"error": stop.code})
        AgentRun.objects.filter(pk=run.pk).update(status=stop.status, error_code=stop.code, ledger=run.ledger if run.ledger else {},
                                                  transcript=run.transcript, plan=run.plan, usage=run.usage, agent=run.agent, updated_at=timezone.now())
    except Exception:
        add_step(run, "error", "Agent 运行出错", "error", {"error": "agent_internal_error"})
        AgentRun.objects.filter(pk=run.pk).update(status="failed", error_code="agent_internal_error", updated_at=timezone.now())
        raise


def decide(run, tool_call_id, approve, note=""):
    """Applies or rejects one pending proposal of a run the caller moved to `applying`; re-queues it when all are decided."""
    proposal = next((p for p in run.pending.get("proposals", []) if p["tool_call_id"] == tool_call_id), None)
    if run.status != "applying" or proposal is None or proposal["decision"] is not None:
        raise ValueError("no_pending_proposal")
    ctx = Context(run)
    step = run.steps.get(index=proposal["step"])
    call = {"id": tool_call_id, "name": proposal["tool"]}
    if approve:
        try:
            outcome = TOOLS[proposal["tool"]]["apply"](ctx, proposal["proposal"])
            proposal["result"], step.status = tool_message(call, {"approved": True, **outcome}), "approved"
        except (ToolError, ValueError, OSError) as exc:
            code = exc.code if isinstance(exc, ToolError) else "apply_failed"
            proposal["result"], step.status = tool_message(call, {"approved": True, "error": code}, True), "failed"
            outcome = {"error": code}
    else:
        outcome = {"approved": False, "note": note[:500]}
        proposal["result"], step.status = tool_message(call, {"approved": False, "user_note": note[:500] or "用户拒绝了这个操作。"}), "rejected"
    proposal["decision"] = "approved" if approve else "rejected"
    step.payload = step.payload | {"outcome": outcome, "note": note[:500]}
    step.save(update_fields=["status", "payload"])
    run.status = "queued" if all(p["decision"] for p in run.pending["proposals"]) else "awaiting_approval"
    save(run, ctx)
    return outcome
