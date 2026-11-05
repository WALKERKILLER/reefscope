"""Versioned analysis Run endpoints. Checkpoints and private paths never serialize."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import AnalysisRun, ModelVersion, Task
from .contracts import SETTINGS
from .queue import retry


def serialize(run):
    return {"run_id": str(run.id), "task_id": run.task_id, "kind": run.model.kind, "status": run.status,
            "progress": run.progress, "attempt": run.attempt, "error_code": run.error_code,
            "config_snapshot": run.config_snapshot, "summary": run.summary,
            "created_at": run.created_at, "updated_at": run.updated_at}


class Models(APIView):
    def get(self, request):
        return Response({"items": list(ModelVersion.objects.order_by("id").values("id", "kind", "sha256", "labels", "framework_version", "metadata"))})


class TaskRuns(APIView):
    def get(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        return Response({"items": [serialize(r) for r in task.analysis_runs.select_related("model").order_by("-created_at")[:100]]})

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        data = request.data
        try:
            kind = data.get("kind") if isinstance(data, dict) else None
            if not isinstance(data, dict) or set(data) - {"kind", "models", "settings"} or kind not in SETTINGS:
                raise ValueError("invalid_run_request")
            models = data.get("models")
            if not isinstance(models, dict) or set(models) != {kind} or not isinstance(models[kind], str):
                raise ValueError("invalid_model")
            model = ModelVersion.objects.filter(pk=models[kind]).first()
            if model is None:
                raise ValueError("unknown_model")
            if model.kind != kind:
                raise ValueError("model_kind_mismatch")
            config = SETTINGS[kind](data.get("settings", {}))
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=400)
        run = AnalysisRun.objects.create(task=task, model=model, config_snapshot={"models": {kind: model.id}, "model_sha256": model.sha256, "settings": config})
        return Response(serialize(run), status=202)


class RunDetail(APIView):
    def get(self, request, run_id):
        return Response(serialize(get_object_or_404(AnalysisRun, pk=run_id)))


class Retry(APIView):
    def post(self, request, run_id):
        get_object_or_404(AnalysisRun, pk=run_id)
        if not retry(run_id):
            return Response({"error": {"code": "retry_not_allowed"}}, status=409)
        return Response(serialize(AnalysisRun.objects.get(pk=run_id)), status=202)


def fish_only(run):
    return None if run.model.kind == "fish" else Response({"error": {"code": "run_kind_not_supported"}}, status=400)


class Tracks(APIView):
    def get(self, request, run_id):
        from .query import page
        run = get_object_or_404(AnalysisRun, pk=run_id)
        if rejected := fish_only(run):
            return rejected
        try:
            return Response(page(run, request.query_params))
        except (ValueError, OSError):
            return Response({"error":{"code":"tracks_unavailable_or_invalid_query"}}, status=400 if run.status == "completed" else 409)


class Heatmap(APIView):
    def get(self, request, run_id):
        import csv
        import io
        import json
        from django.http import HttpResponse
        from .heatmap import integrate
        from .query import parameters, records
        run = get_object_or_404(AnalysisRun, pk=run_id)
        if rejected := fish_only(run):
            return rejected
        try:
            if set(request.query_params) - {"start_ms", "end_ms", "track_id", "class_id", "roi", "width", "height", "export"}:
                raise ValueError("unknown_parameter")
            options = parameters(request.query_params)
            config = run.config_snapshot["settings"]
            result = integrate(records(run), **options, width=int(request.query_params.get("width",64)),
                               height=int(request.query_params.get("height",36)),
                               allowed_gap_seconds=config["allowed_gap_seconds"],camera_motion=config["camera_motion"])
            result.update(run_id=str(run.pk), model_id=run.model_id, model_sha256=run.config_snapshot["model_sha256"])
            if request.query_params.get("export", "json") == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                metadata_keys = ["start_ms", "end_ms", "model_id", "model_sha256", "algorithm_version", "camera_motion", "coordinate_space", "value_unit", "track_filter", "class_id", "roi", "width", "height", "integration_steps", "allowed_gap_seconds"]
                writer.writerow(["run_id","x","y","track_seconds",*metadata_keys])
                for y,row in enumerate(result["values_raw"]):
                    for x,value in enumerate(row):
                        writer.writerow([run.pk,x,y,value,*[json.dumps(result[key],ensure_ascii=False) if key == "roi" else result[key] for key in metadata_keys]])
                response = HttpResponse(output.getvalue(),content_type="text/csv; charset=utf-8")
                response["Content-Disposition"] = 'attachment; filename="heatmap.csv"'
                return response
            if request.query_params.get("export", "json") != "json":
                raise ValueError("invalid_format")
            return Response(result)
        except (ValueError, OSError):
            return Response({"error":{"code":"heatmap_unavailable_or_invalid_query"}}, status=400 if run.status == "completed" else 409)


class Summary(APIView):
    def get(self, request, run_id):
        from django.http import JsonResponse
        from .query import parameters
        from .summary import summarize
        from . import coral_query
        run = get_object_or_404(AnalysisRun, pk=run_id)
        try:
            if run.model.kind == "coral":
                result = coral_query.summarize(run, coral_query.window(request.query_params))
            elif set(request.query_params) - {"start_ms","end_ms","track_id","class_id","roi","export"}:
                raise ValueError("unknown_parameter")
            else:
                result = summarize(run, parameters(request.query_params))
            response = JsonResponse(result,json_dumps_params={"ensure_ascii":False,"allow_nan":False})
            if request.query_params.get("export") == "json":
                response["Content-Disposition"] = 'attachment; filename="analysis_report.json"'
            elif "export" in request.query_params:
                raise ValueError("invalid_export")
            return response
        except (ValueError,OSError):
            return Response({"error":{"code":"summary_unavailable_or_invalid_query"}},status=400 if run.status == "completed" else 409)


class Masks(APIView):
    """Without `frame`, the sampled-frame index; with it, that frame's single-channel class-index PNG."""
    def get(self, request, run_id):
        from django.http import FileResponse
        from . import coral_query
        run = get_object_or_404(AnalysisRun, pk=run_id)
        if run.model.kind != "coral":
            return Response({"error": {"code": "run_kind_not_supported"}}, status=400)
        if run.status != "completed":
            return Response({"error": {"code": "masks_unavailable"}}, status=409)
        try:
            if set(request.query_params) - {"frame"}:
                raise ValueError("unknown_parameter")
            if "frame" not in request.query_params:
                keys = ("frame", "timestamp_ms", "width", "height", "background_separated", "guard_score", "pixel_counts", "mask_sha256")
                return Response({"run_id": str(run.pk), "labels": run.model.labels, "items": [{key: row[key] for key in keys} for row in coral_query.frames(run)]})
            path, record = coral_query.mask(run, int(request.query_params["frame"]))
        except LookupError:
            return Response({"error": {"code": "unknown_frame"}}, status=404)
        except (ValueError, OSError):
            return Response({"error": {"code": "masks_unavailable_or_invalid_query"}}, status=400)
        response = FileResponse(path.open("rb"), content_type="image/png")
        # Attempt artifacts never change after publication.
        response["Cache-Control"] = "private, max-age=31536000, immutable"
        response["ETag"] = f'"{record["mask_sha256"]}"'
        return response
