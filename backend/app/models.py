from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        PROCESSING = "processing", "处理中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"

    original_filename = models.CharField(max_length=255)
    uploaded_video_path = models.CharField(max_length=500)
    result_video_path = models.CharField(max_length=500, blank=True)
    detections = models.JSONField(default=list, blank=True)
    progress = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.original_filename}"
