#!/usr/bin/env python
"""Utility Django untuk menjalankan perintah administratif."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Django tidak terpasang. Aktifkan virtualenv lalu jalankan: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
