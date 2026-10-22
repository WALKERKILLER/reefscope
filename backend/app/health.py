"""进程存活检查，不加载模型、不暴露运行环境。"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
