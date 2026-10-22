from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "status", "created_at", "updated_at")
    search_fields = ("original_filename",)
    list_filter = ("status",)
