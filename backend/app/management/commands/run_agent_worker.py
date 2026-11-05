"""Observation-agent Worker: runs agent loops outside the Web server and resumes them after approval."""
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from app.agent.loop import claim, process


class Command(BaseCommand):
    help = "Process queued observation-agent runs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            run = claim()
            if run:
                try:
                    process(run)
                except Exception:
                    self.stderr.write("agent run failed: agent_internal_error")
            if options["once"]:
                return
            if run is None:
                time.sleep(1)
