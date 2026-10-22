from django.urls import path

from .health import health
from .analysis.api import Models, TaskRuns, RunDetail, Retry, Tracks, Heatmap

from .views import PipelineConfigView, ProcessTaskView, TaskBatchActionView, TaskDetailView, TaskListView, UploadVideoView

urlpatterns = [
    path("v1/analysis-runs/<uuid:run_id>/tracks", Tracks.as_view(), name="analysis-tracks"),
    path("v1/analysis-runs/<uuid:run_id>/heatmap", Heatmap.as_view(), name="analysis-heatmap"),
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
