"""Versioned fish Run endpoints. Checkpoints and private paths never serialize."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import AnalysisRun, ModelVersion, Task
from .contracts import validate_settings
from .queue import retry


def serialize(run):
    return {"run_id": str(run.id), "task_id": run.task_id, "kind": "fish", "status": run.status,
            "progress": run.progress, "attempt": run.attempt, "error_code": run.error_code,
            "config_snapshot": run.config_snapshot, "summary": run.summary,
            "created_at": run.created_at, "updated_at": run.updated_at}


class Models(APIView):
    def get(self, request):
        return Response({"items": list(ModelVersion.objects.order_by("id").values("id", "sha256", "labels", "framework_version"))})


class TaskRuns(APIView):
    def get(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        return Response({"items": [serialize(r) for r in task.analysis_runs.order_by("-created_at")[:100]]})

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        data = request.data
        try:
            if not isinstance(data, dict) or set(data) - {"kind", "models", "settings"} or data.get("kind") != "fish":
                raise ValueError("invalid_run_request")
            models = data.get("models")
            if not isinstance(models, dict) or set(models) != {"fish"} or not isinstance(models["fish"], str):
                raise ValueError("invalid_model")
            model = ModelVersion.objects.filter(pk=models["fish"]).first()
            if model is None:
                raise ValueError("unknown_model")
            config = validate_settings(data.get("settings", {}))
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=400)
        run = AnalysisRun.objects.create(task=task, model=model, config_snapshot={"models": {"fish": model.id}, "model_sha256": model.sha256, "settings": config})
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


class Tracks(APIView):
    def get(self, request, run_id):
        from .query import page
        run = get_object_or_404(AnalysisRun, pk=run_id)
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
