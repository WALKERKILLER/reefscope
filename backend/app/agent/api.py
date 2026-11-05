"""Agent sessions per site, runs with incremental steps, approval decisions and cancellation."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

import math
import uuid

from app.models import AgentRun, AgentSession, AnalysisRun, ObservationSite, Task
from app.observation.agent import config as agent_config
from . import loop

ACTIVE = ("queued", "running", "awaiting_approval", "applying")


def error(code, status=400):
    return Response({"error": {"code": code}}, status=status)


def serialize_step(step):
    return {"index": step.index, "kind": step.kind, "title": step.title, "status": step.status, "payload": step.payload,
            "duration_ms": step.duration_ms, "created_at": step.created_at}


def serialize_run(run, after=0):
    return {"id": str(run.pk), "session_id": str(run.session_id), "goal": run.goal, "status": run.status, "error_code": run.error_code, "context": run.context,
            "plan": run.plan, "answer": run.answer, "usage": run.usage, "agent": run.agent, "created_at": run.created_at, "updated_at": run.updated_at,
            "ledger": run.ledger.get("metrics", {}), "steps": [serialize_step(step) for step in run.steps.filter(index__gt=after).order_by("index")],
            "limits": {"turns": loop.MAX_TURNS, "tool_calls": loop.MAX_TOOL_CALLS, "revisions": loop.MAX_REVISIONS}}


def serialize_session(session, runs=False):
    item = {"id": str(session.pk), "site_id": session.site_id and str(session.site_id), "site_name": session.site.name if session.site_id else None,
            "task_id": session.task_id, "title": session.title, "created_at": session.created_at,
            "updated_at": session.updated_at, "run_count": session.runs.count()}
    if runs:
        item["runs"] = [serialize_run(run) for run in session.runs.order_by("created_at")]
    return item


def goal_text(data):
    text = data.get("text") if isinstance(data, dict) else None
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise ValueError("invalid_message")
    return text.strip()


def playback_context(session, data):
    """The wall's view at send time: the session's video, its completed runs and the playback position."""
    if session.task_id is None:
        return {}
    raw = data.get("context") or {}
    if not isinstance(raw, dict) or set(raw) - {"current_time_s", "fish_run_id", "coral_run_id"}:
        raise ValueError("invalid_context")
    now = raw.get("current_time_s", 0)
    if type(now) not in (int, float) or not math.isfinite(now) or not 0 <= now <= 86400:
        raise ValueError("invalid_context")
    context = {"task_id": session.task_id, "current_time_s": round(float(now), 3)}
    for key, kind in (("fish_run_id", "fish"), ("coral_run_id", "coral")):
        value = raw.get(key)
        if value is None:
            continue
        try:
            run_id = uuid.UUID(str(value))
        except ValueError:
            raise ValueError("invalid_context") from None
        if AnalysisRun.objects.filter(pk=run_id, task_id=session.task_id, model__kind=kind, status="completed").exists():
            context[key] = str(run_id)
    return context


def site_of(data):
    value = data.get("site_id")
    if value is None:
        return None
    try:
        return ObservationSite.objects.get(pk=uuid.UUID(str(value)))
    except (ValueError, ObservationSite.DoesNotExist):
        raise ValueError("unknown_site") from None


def start_run(session, text, context=None):
    """A follow-up continues the previous run's transcript and evidence ledger."""
    previous = session.runs.order_by("-created_at").first()
    transcript = list(previous.transcript) if previous and previous.status == "completed" else []
    ledger = previous.ledger if previous else {}
    transcript.append({"role": "user", "text": text})
    return AgentRun.objects.create(session=session, goal=text, transcript=transcript, ledger=ledger, context=context or {})


class SiteSessions(APIView):
    def get(self, request, site_id):
        site = get_object_or_404(ObservationSite, pk=site_id)
        return Response({"items": [serialize_session(s) for s in site.agent_sessions.select_related("site").order_by("-updated_at")[:50]]})

    def post(self, request, site_id):
        site = get_object_or_404(ObservationSite, pk=site_id)
        if not agent_config().enabled:
            return error("agent_disabled", 409)
        try:
            text = goal_text(request.data)
        except ValueError as exc:
            return error(str(exc))
        with transaction.atomic():
            session = AgentSession.objects.create(site=site, title=text[:60])
            start_run(session, text)
        return Response(serialize_session(session, runs=True), status=201)


class TaskSessions(APIView):
    """Sessions started from a video on the monitoring wall."""
    def get(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        return Response({"items": [serialize_session(s) for s in task.agent_sessions.select_related("site").order_by("-updated_at")[:50]]})

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        if not agent_config().enabled:
            return error("agent_disabled", 409)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            text, site = goal_text(data), site_of(data)
            session = AgentSession(task=task, site=site, title=text[:60])
            context = playback_context(session, data)
        except ValueError as exc:
            return error(str(exc))
        with transaction.atomic():
            session.save()
            start_run(session, text, context)
        return Response(serialize_session(session, runs=True), status=201)


class SessionDetail(APIView):
    def get(self, request, session_id):
        return Response(serialize_session(get_object_or_404(AgentSession, pk=session_id), runs=True))

    def patch(self, request, session_id):
        """Files a session to a site (or removes it), which saving a report requires."""
        session = get_object_or_404(AgentSession, pk=session_id)
        data = request.data if isinstance(request.data, dict) else {}
        if set(data) != {"site_id"}:
            return error("invalid_session_update")
        if session.task_id is None:
            return error("site_session_fixed", 409)
        try:
            session.site = site_of(data)
        except ValueError as exc:
            return error(str(exc))
        session.save(update_fields=["site", "updated_at"])
        return Response(serialize_session(session))

    def delete(self, request, session_id):
        session = get_object_or_404(AgentSession, pk=session_id)
        if session.runs.filter(status__in=ACTIVE).exists():
            return error("session_active", 409)
        session.delete()
        return Response(status=204)


class SessionMessages(APIView):
    def post(self, request, session_id):
        session = get_object_or_404(AgentSession, pk=session_id)
        if not agent_config().enabled:
            return error("agent_disabled", 409)
        if session.runs.filter(status__in=ACTIVE).exists():
            return error("run_in_progress", 409)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            run = start_run(session, goal_text(data), playback_context(session, data))
        except ValueError as exc:
            return error(str(exc))
        AgentSession.objects.filter(pk=session.pk).update(updated_at=timezone.now())
        return Response(serialize_run(run), status=201)


class RunDetail(APIView):
    def get(self, request, run_id):
        run = get_object_or_404(AgentRun, pk=run_id)
        try:
            after = max(0, int(request.query_params.get("after", 0)))
        except ValueError:
            return error("invalid_query")
        return Response(serialize_run(run, after))


class RunDecision(APIView):
    def post(self, request, run_id):
        get_object_or_404(AgentRun, pk=run_id)
        data = request.data if isinstance(request.data, dict) else {}
        if set(data) - {"tool_call_id", "decision", "note"} or data.get("decision") not in ("approve", "reject") or not isinstance(data.get("tool_call_id"), str) \
                or not isinstance(data.get("note", ""), str):
            return error("invalid_decision")
        # A status swap claims the run instead of a transaction: SQLite cannot upgrade a read
        # transaction to a write while the agent Worker is writing, and applying a proposal reads first.
        if not AgentRun.objects.filter(pk=run_id, status="awaiting_approval").update(status="applying", updated_at=timezone.now()):
            return error("no_pending_proposal", 409)
        run = AgentRun.objects.select_related("session__site").get(pk=run_id)
        try:
            outcome = loop.decide(run, data["tool_call_id"], data["decision"] == "approve", data.get("note", ""))
        except BaseException as exc:
            AgentRun.objects.filter(pk=run_id, status="applying").update(status="awaiting_approval")
            if isinstance(exc, ValueError):
                return error(str(exc), 409)
            raise
        return Response({"outcome": outcome, "run": serialize_run(run)})


class RunCancel(APIView):
    def post(self, request, run_id):
        run = get_object_or_404(AgentRun, pk=run_id)
        if run.status in ("queued", "awaiting_approval"):
            AgentRun.objects.filter(pk=run.pk, status=run.status).update(status="cancelled", error_code="cancelled_by_user", updated_at=timezone.now())
            loop.add_step(run, "error", "已停止", "cancelled", {"error": "cancelled_by_user"})
        elif run.status == "running":
            AgentRun.objects.filter(pk=run.pk).update(cancel_requested=True)
        else:
            return error("run_not_active", 409)
        return Response(serialize_run(AgentRun.objects.get(pk=run.pk)))
