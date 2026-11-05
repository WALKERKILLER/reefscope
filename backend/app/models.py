import uuid

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


class ModelVersion(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    weight_path = models.CharField(max_length=1000)
    sha256 = models.CharField(max_length=64)
    labels = models.JSONField()
    framework_version = models.CharField(max_length=40)
    # A Run's kind is its model's kind; fish and coral checkpoints never share an adapter.
    kind = models.CharField(max_length=12, default="fish")
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalysisRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="analysis_runs")
    model = models.ForeignKey(ModelVersion, on_delete=models.PROTECT)
    config_snapshot = models.JSONField()
    status = models.CharField(max_length=12, default="queued", db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)
    attempt = models.PositiveSmallIntegerField(default=0)
    attempt_token = models.UUIDField(null=True, editable=False)
    lease_expires_at = models.DateTimeField(null=True)
    summary = models.JSONField(default=dict)
    error_code = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ImmutableResearchRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if not self._state.adding:
            raise ValidationError("immutable_research_record")
        return super().save(*args, **kwargs)


class TrainingRun(ImmutableResearchRecord):
    model = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, related_name="training_runs")
    snapshot = models.JSONField()
    source_hashes = models.JSONField()


class EvaluationRun(ImmutableResearchRecord):
    model = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, related_name="evaluations")
    analysis_run = models.ForeignKey(AnalysisRun, null=True, on_delete=models.PROTECT)
    dataset_version = models.CharField(max_length=80)
    dataset_sha256 = models.CharField(max_length=64)
    protocol_id = models.CharField(max_length=80)
    metrics = models.JSONField()
    config = models.JSONField()
    source_hashes = models.JSONField()
    missing_inputs = models.JSONField(default=list)


class TrainingReport(ImmutableResearchRecord):
    model = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, related_name="reports")
    training_run = models.ForeignKey(TrainingRun, null=True, on_delete=models.PROTECT)
    evaluation_run = models.ForeignKey(EvaluationRun, null=True, on_delete=models.PROTECT)
    payload = models.JSONField()
    markdown = models.TextField()
    html = models.TextField()


class ObservationSite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    # Coordinates stay on the platform; observation-report prompts never include them.
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    depth_m = models.FloatField(null=True)
    notes = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)


class ObservationReport(ImmutableResearchRecord):
    site = models.ForeignKey(ObservationSite, on_delete=models.PROTECT, related_name="reports")
    observed_on = models.DateField()
    payload = models.JSONField()
    markdown = models.TextField()
    html = models.TextField()


class ReportAgentConfig(models.Model):
    """Singleton (pk=1). The API key lives in a separate owner-only file, bound to `key_bound_url`."""
    api_format = models.CharField(max_length=24, default="openai_chat")
    base_url = models.CharField(max_length=500, blank=True)
    model = models.CharField(max_length=120, blank=True)
    timeout_seconds = models.PositiveSmallIntegerField(default=60)
    max_output_tokens = models.PositiveIntegerField(default=4096)
    enabled = models.BooleanField(default=False)
    key_hint = models.CharField(max_length=8, blank=True)
    key_bound_url = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AgentSession(models.Model):
    """A conversation with the observation agent about one site; runs share its history and evidence."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(ObservationSite, on_delete=models.CASCADE, related_name="agent_sessions")
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AgentRun(models.Model):
    """One user turn: the agent loop runs in `run_agent_worker` and may pause for approval."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name="runs")
    goal = models.TextField(max_length=4000)
    status = models.CharField(max_length=20, default="queued", db_index=True)
    attempt_token = models.UUIDField(null=True, editable=False)
    lease_expires_at = models.DateTimeField(null=True)
    cancel_requested = models.BooleanField(default=False)
    transcript = models.JSONField(default=list)
    ledger = models.JSONField(default=dict)
    plan = models.JSONField(default=list)
    pending = models.JSONField(default=dict)
    answer = models.JSONField(null=True)
    usage = models.JSONField(default=dict)
    agent = models.JSONField(default=dict)
    error_code = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AgentStep(models.Model):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="steps")
    index = models.PositiveIntegerField()
    kind = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="done")
    payload = models.JSONField(default=dict)
    duration_ms = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "index"], name="agent_step_order")]
