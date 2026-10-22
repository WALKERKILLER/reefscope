from django.urls import path

from .health import health

from .views import PipelineConfigView, ProcessTaskView, TaskBatchActionView, TaskDetailView, TaskListView, UploadVideoView

urlpatterns = [
    path("health", health, name="health"),
    path("tasks", TaskListView.as_view(), name="task-list"),
    path("tasks/actions", TaskBatchActionView.as_view(), name="task-batch-actions"),
    path("config", PipelineConfigView.as_view(), name="pipeline-config"),
    path("upload", UploadVideoView.as_view(), name="upload-video"),
    path("process/<int:task_id>", ProcessTaskView.as_view(), name="process-task"),
    path("task/<int:task_id>", TaskDetailView.as_view(), name="task-detail"),
]
