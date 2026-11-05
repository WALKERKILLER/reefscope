from django.urls import path

from .health import health
from .analysis.report_api import ModelHistory, ReportDetail, ReportExport, EvaluationDetail
from .analysis.api import Models, TaskRuns, RunDetail, Retry, Tracks, Heatmap, Summary, Masks

from .observation import api as observation

from .views import PipelineConfigView, ProcessTaskView, TaskBatchActionView, TaskDetailView, TaskListView, UploadVideoView

urlpatterns = [
    path("v1/report-agent/config", observation.AgentConfig.as_view(), name="report-agent-config"),
    path("v1/report-agent/test", observation.AgentTest.as_view(), name="report-agent-test"),
    path("v1/sites", observation.Sites.as_view(), name="observation-sites"),
    path("v1/sites/<uuid:site_id>", observation.SiteDetail.as_view(), name="observation-site"),
    path("v1/sites/<uuid:site_id>/reports", observation.SiteReports.as_view(), name="observation-site-reports"),
    path("v1/observation-reports/candidates", observation.Candidates.as_view(), name="observation-candidates"),
    path("v1/observation-reports/preview", observation.ReportPreview.as_view(), name="observation-preview"),
    path("v1/observation-reports", observation.Reports.as_view(), name="observation-reports"),
    path("v1/observation-reports/<uuid:report_id>", observation.ReportDetail.as_view(), name="observation-report"),
    path("v1/observation-reports/<uuid:report_id>/export", observation.ReportExport.as_view(), name="observation-report-export"),
    path("v1/model-versions/<str:model_id>/history", ModelHistory.as_view(), name="model-research-history"),
    path("v1/reports/<uuid:report_id>", ReportDetail.as_view(), name="training-report-detail"),
    path("v1/reports/<uuid:report_id>/export", ReportExport.as_view(), name="training-report-export"),
    path("v1/evaluations/<uuid:evaluation_id>", EvaluationDetail.as_view(), name="evaluation-detail"),
    path("v1/analysis-runs/<uuid:run_id>/tracks", Tracks.as_view(), name="analysis-tracks"),
    path("v1/analysis-runs/<uuid:run_id>/heatmap", Heatmap.as_view(), name="analysis-heatmap"),
    path("v1/analysis-runs/<uuid:run_id>/summary", Summary.as_view(), name="analysis-summary"),
    path("v1/analysis-runs/<uuid:run_id>/masks", Masks.as_view(), name="analysis-masks"),
    path("v1/models", Models.as_view(), name="analysis-models"),
    path("v1/tasks/<int:task_id>/analysis-runs", TaskRuns.as_view(), name="analysis-runs"),
    path("v1/analysis-runs/<uuid:run_id>", RunDetail.as_view(), name="analysis-detail"),
    path("v1/analysis-runs/<uuid:run_id>/retry", Retry.as_view(), name="analysis-retry"),
    path("health", health, name="health"),
    path("tasks", TaskListView.as_view(), name="task-list"),
    path("tasks/actions", TaskBatchActionView.as_view(), name="task-batch-actions"),
    path("config", PipelineConfigView.as_view(), name="pipeline-config"),
    path("upload", UploadVideoView.as_view(), name="upload-video"),
    path("process/<int:task_id>", ProcessTaskView.as_view(), name="process-task"),
    path("task/<int:task_id>", TaskDetailView.as_view(), name="task-detail"),
]
