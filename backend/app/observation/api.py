"""Observation sites, report-agent configuration and immutable observation reports."""
import datetime
import math
import uuid

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import AnalysisRun, ObservationReport, ObservationSite
from . import agent, facts, report


def error(code, status=400):
    return Response({"error": {"code": code}}, status=status)


class AgentConfig(APIView):
    def get(self, request):
        return Response(agent.serialize(agent.config()))

    def put(self, request):
        try:
            item = agent.update(agent.config(), request.data)
        except ValueError as exc:
            return error(str(exc))
        return Response(agent.serialize(item))


class AgentTest(APIView):
    """Tests the saved configuration only, so an unsaved URL never receives the stored key."""
    def post(self, request):
        return Response(agent.test_connection(agent.config()))


def serialize_site(site):
    latest = site.reports.order_by("-observed_on").values_list("observed_on", flat=True).first()
    return {"id": str(site.pk), "name": site.name, "latitude": site.latitude, "longitude": site.longitude, "depth_m": site.depth_m,
            "notes": site.notes, "created_at": site.created_at, "report_count": site.reports.count(), "last_observed_on": latest}


def site_fields(data, partial):
    allowed = {"name", "latitude", "longitude", "depth_m", "notes"}
    if not isinstance(data, dict) or set(data) - allowed or (not partial and "name" not in data):
        raise ValueError("invalid_site")
    result = {}
    if "name" in data:
        if not isinstance(data["name"], str) or not 1 <= len(data["name"].strip()) <= 80:
            raise ValueError("invalid_site_name")
        result["name"] = data["name"].strip()
    for key, (low, high) in {"latitude": (-90, 90), "longitude": (-180, 180), "depth_m": (0, 200)}.items():
        if key in data:
            value = data[key]
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high):
                raise ValueError(f"invalid_{key}")
            result[key] = value
    if "notes" in data:
        if not isinstance(data["notes"], str) or len(data["notes"]) > 2000:
            raise ValueError("invalid_notes")
        result["notes"] = data["notes"]
    return result


class Sites(APIView):
    def get(self, request):
        return Response({"items": [serialize_site(site) for site in ObservationSite.objects.order_by("name")]})

    def post(self, request):
        try:
            with transaction.atomic():
                site = ObservationSite.objects.create(**site_fields(request.data, partial=False))
        except ValueError as exc:
            return error(str(exc))
        except IntegrityError:
            return error("site_name_taken", 409)
        return Response(serialize_site(site), status=201)


class SiteDetail(APIView):
    def get(self, request, site_id):
        return Response(serialize_site(get_object_or_404(ObservationSite, pk=site_id)))

    def patch(self, request, site_id):
        site = get_object_or_404(ObservationSite, pk=site_id)
        try:
            for key, value in site_fields(request.data, partial=True).items():
                setattr(site, key, value)
            with transaction.atomic():
                site.save()
        except ValueError as exc:
            return error(str(exc))
        except IntegrityError:
            return error("site_name_taken", 409)
        return Response(serialize_site(site))

    def delete(self, request, site_id):
        site = get_object_or_404(ObservationSite, pk=site_id)
        if site.reports.exists():
            return error("site_has_reports", 409)
        site.delete()
        return Response(status=204)


def list_item(item):
    metrics = item.payload["facts"]["metrics"]
    pick = lambda key: metrics[key]["display"] if key in metrics else None
    return {"id": str(item.pk), "observed_on": item.observed_on, "created_at": item.created_at, "title": item.payload["title"],
            "agent_status": "agent_run" if item.payload["agent"].get("mode") == "agent_run" else item.payload["agent"]["status"], "human_review_status": item.payload["human_review_status"],
            "video_count": len(item.payload["facts"]["videos"]), "mean_count": pick("site.fish.mean_count"),
            "bleached_coral_fraction": pick("site.coral.bleached_coral_fraction")}


class SiteReports(APIView):
    def get(self, request, site_id):
        site = get_object_or_404(ObservationSite, pk=site_id)
        return Response({"items": [list_item(item) for item in site.reports.order_by("-observed_on", "-created_at")[:200]]})


class Candidates(APIView):
    """Completed Runs grouped by video, newest first; the picker for a new report."""
    def get(self, request):
        groups = {}
        for run in AnalysisRun.objects.filter(status="completed").select_related("task", "model").order_by("-created_at")[:500]:
            group = groups.setdefault(run.task_id, {"task_id": run.task_id, "filename": run.task.original_filename, "runs": []})
            group["runs"].append({"run_id": str(run.pk), "kind": run.model.kind, "model_id": run.model_id, "created_at": run.created_at,
                                  "camera_motion": run.config_snapshot["settings"]["camera_motion"]})
        return Response({"items": list(groups.values())})


def report_request(data):
    if not isinstance(data, dict) or set(data) - {"site_id", "observed_on", "run_ids", "environment", "use_agent"}:
        raise ValueError("invalid_report_request")
    try:
        site = ObservationSite.objects.filter(pk=uuid.UUID(str(data.get("site_id")))).first()
    except ValueError:
        site = None
    if site is None:
        raise LookupError("unknown_site")
    try:
        observed_on = datetime.date.fromisoformat(data.get("observed_on"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_observed_on") from exc
    run_ids = data.get("run_ids")
    if not isinstance(run_ids, list) or not 1 <= len(run_ids) <= facts.MAX_RUNS or len(set(map(str, run_ids))) != len(run_ids):
        raise ValueError("invalid_run_ids")
    try:
        keys = [uuid.UUID(str(value)) for value in run_ids]
    except ValueError as exc:
        raise ValueError("invalid_run_ids") from exc
    found = {run.pk: run for run in AnalysisRun.objects.filter(pk__in=keys).select_related("task", "model")}
    if len(found) != len(keys):
        raise LookupError("unknown_run")
    runs = [found[key] for key in keys]
    if any(run.status != "completed" for run in runs):
        raise PermissionError("run_not_completed")
    use_agent = data.get("use_agent", False)
    if type(use_agent) is not bool:
        raise ValueError("invalid_use_agent")
    return site, observed_on, runs, facts.validate_environment(data.get("environment")), use_agent


def build_facts(data):
    site, observed_on, runs, environment, use_agent = report_request(data)
    try:
        return site, observed_on, facts.build(site, observed_on, runs, environment), use_agent
    except ValueError as exc:
        if str(exc) == "duplicate_run_kind_for_video":
            raise
        raise PermissionError("run_artifacts_unavailable") from exc
    except OSError as exc:
        raise PermissionError("run_artifacts_unavailable") from exc


def failure(exc):
    status = 404 if isinstance(exc, LookupError) else 409 if isinstance(exc, PermissionError) else 400
    return error(str(exc), status)


class ReportPreview(APIView):
    """Deterministic facts for the form; nothing is stored and nothing leaves the platform."""
    def post(self, request):
        try:
            _, _, built, _ = build_facts(request.data)
        except (ValueError, LookupError, PermissionError) as exc:
            return failure(exc)
        return Response(built)


class Reports(APIView):
    def post(self, request):
        try:
            site, observed_on, built, use_agent = build_facts(request.data)
        except (ValueError, LookupError, PermissionError) as exc:
            return failure(exc)
        config = agent.config()
        if not use_agent:
            record = {"status": "disabled"}
        elif not config.enabled:
            return error("agent_disabled", 409)
        else:
            record = agent.narrate(config, built)
        payload, markdown, html = report.make(built, record)
        item = ObservationReport.objects.create(site=site, observed_on=observed_on, payload=payload, markdown=markdown, html=html)
        return Response(detail(item), status=201)


def detail(item):
    return {"report_id": str(item.pk), "created_at": item.created_at, "site_id": str(item.site_id), "observed_on": item.observed_on, **item.payload}


class ReportDetail(APIView):
    def get(self, request, report_id):
        return Response(detail(get_object_or_404(ObservationReport, pk=report_id)))


class ReportExport(APIView):
    def get(self, request, report_id):
        item = get_object_or_404(ObservationReport, pk=report_id)
        kind = request.query_params.get("export", "markdown")
        if kind not in {"markdown", "html"}:
            return error("unsupported_export")
        response = HttpResponse(item.html if kind == "html" else item.markdown,
                                content_type="text/html; charset=utf-8" if kind == "html" else "text/markdown; charset=utf-8")
        if kind == "markdown":
            response["Content-Disposition"] = 'attachment; filename="observation-report.md"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"
        return response
