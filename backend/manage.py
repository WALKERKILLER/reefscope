#!/usr/bin/env python
"""Django 管理入口。"""
import os
import sys


def _ensure_supported_python() -> None:
    if os.environ.get("SKIP_PYTHON_VERSION_CHECK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    current = sys.version_info
    if current.major != 3 or current.minor != 12:
        version_text = f"{current.major}.{current.minor}.{current.micro}"
        raise RuntimeError(
            "当前后端仅支持 Python 3.12。"
            f"检测到的解释器版本为 {version_text}。"
            "请使用 `uv venv --python 3.12` 重新创建虚拟环境后再启动。"
        )


def main():
    _ensure_supported_python()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
