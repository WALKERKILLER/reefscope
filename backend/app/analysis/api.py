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
