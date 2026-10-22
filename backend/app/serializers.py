from rest_framework import serializers

from .models import Task
from .services.task_runner import get_runtime_progress


class TaskSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(source="id", read_only=True)
    progress = serializers.SerializerMethodField()
    progress_current_frame = serializers.SerializerMethodField()
    progress_total_frames = serializers.SerializerMethodField()
    progress_message = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "task_id",
            "original_filename",
            "uploaded_video_path",
            "result_video_path",
            "detections",
            "progress",
            "progress_current_frame",
            "progress_total_frames",
            "progress_message",
            "status",
            "created_at",
            "updated_at",
        ]

    def _runtime(self, obj: Task) -> dict:
        return get_runtime_progress(obj.id)

    def get_progress(self, obj: Task) -> int:
        return int(self._runtime(obj).get("progress", obj.progress))

    def get_progress_current_frame(self, obj: Task) -> int:
        return int(self._runtime(obj).get("current_frame", 0) or 0)

    def get_progress_total_frames(self, obj: Task) -> int:
        return int(self._runtime(obj).get("total_frames", 0) or 0)

    def get_progress_message(self, obj: Task) -> str:
        return str(self._runtime(obj).get("message", "") or "")
