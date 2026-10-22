"""Conditional updates fence late Workers, including on SQLite."""
from datetime import timedelta
from uuid import uuid4

from django.db.models import F
from django.utils import timezone

from app.models import AnalysisRun

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3


def expire_runs():
    return AnalysisRun.objects.filter(status="running", lease_expires_at__lte=timezone.now()).update(
        status="failed", error_code="worker_lease_expired", updated_at=timezone.now()
    )


def claim_run():
    expire_runs()
    for run_id in AnalysisRun.objects.filter(status="queued", attempt__lt=MAX_ATTEMPTS).order_by("created_at").values_list("id", flat=True)[:32]:
        token = uuid4()
        now = timezone.now()
        changed = AnalysisRun.objects.filter(pk=run_id, status="queued", attempt__lt=MAX_ATTEMPTS).update(
            status="running", attempt=F("attempt") + 1, attempt_token=token,
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS), progress=0,
            error_code="", updated_at=now,
        )
        if changed:
            return AnalysisRun.objects.select_related("model", "task").get(pk=run_id)
    return None


def owned(run):
    return AnalysisRun.objects.filter(pk=run.pk, status="running", attempt_token=run.attempt_token, lease_expires_at__gt=timezone.now())


def heartbeat(run, progress):
    now = timezone.now()
    if not owned(run).update(progress=min(99, max(0, int(progress))), lease_expires_at=now + timedelta(seconds=LEASE_SECONDS), updated_at=now):
        raise ValueError("worker_lease_lost")


def finish(run, summary):
    if not owned(run).update(status="completed", progress=100, summary=summary, error_code="", updated_at=timezone.now()):
        raise ValueError("worker_lease_lost")


def fail(run, code):
    owned(run).update(status="failed", error_code=code, updated_at=timezone.now())


def retry(run_id):
    return AnalysisRun.objects.filter(pk=run_id, status="failed", attempt__lt=MAX_ATTEMPTS).update(
        status="queued", progress=0, summary={}, error_code="", lease_expires_at=None, updated_at=timezone.now()
    )
