"""Read-only research history and escaped exports; no filesystem path parameters."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import ModelVersion, TrainingRun, EvaluationRun, TrainingReport


class ModelHistory(APIView):
    def get(self, request, model_id):
        model = get_object_or_404(ModelVersion, pk=model_id)
        return Response({"model_id":model.pk,"model_sha256":model.sha256,
            "training_runs":[{"id":str(r.pk),"created_at":r.created_at,"epochs":len(r.snapshot["epochs"]),"selection":r.snapshot["selection"],"missing_inputs":r.snapshot["missing_inputs"]} for r in model.training_runs.order_by("-created_at")[:100]],
            "evaluations":[{"id":str(e.pk),"dataset_version":e.dataset_version,"dataset_sha256":e.dataset_sha256,"protocol_id":e.protocol_id,"metrics":e.metrics,"missing_inputs":e.missing_inputs,"created_at":e.created_at} for e in model.evaluations.order_by("-created_at")[:100]],
            "reports":[{"id":str(r.pk),"training_run_id":str(r.training_run_id) if r.training_run_id else None,"evaluation_run_id":str(r.evaluation_run_id) if r.evaluation_run_id else None,"template_version":r.payload["template_version"],"human_review_status":r.payload["human_review_status"],"created_at":r.created_at} for r in model.reports.order_by("-created_at")[:100]]})


class ReportDetail(APIView):
    def get(self, request, report_id):
        report = get_object_or_404(TrainingReport, pk=report_id)
        return Response({"report_id":str(report.pk),"created_at":report.created_at,**report.payload})


class ReportExport(APIView):
    def get(self, request, report_id):
        report = get_object_or_404(TrainingReport, pk=report_id)
        kind = request.query_params.get("export","markdown")
        if kind not in {"markdown","html"}:
            return Response({"error":{"code":"unsupported_export; use printable HTML for browser PDF"}},status=400)
        response = HttpResponse(report.html if kind == "html" else report.markdown, content_type="text/html; charset=utf-8" if kind == "html" else "text/markdown; charset=utf-8")
        if kind == "markdown":
            response["Content-Disposition"] = 'attachment; filename="training-report.md"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"
        return response


class EvaluationDetail(APIView):
    def get(self, request, evaluation_id):
        e = get_object_or_404(EvaluationRun, pk=evaluation_id)
        return Response({"evaluation_id":str(e.pk),"model_id":e.model_id,"dataset_version":e.dataset_version,
                         "dataset_sha256":e.dataset_sha256,"protocol_id":e.protocol_id,"metrics":e.metrics,
                         "config":e.config,"source_hashes":e.source_hashes,"missing_inputs":e.missing_inputs})
