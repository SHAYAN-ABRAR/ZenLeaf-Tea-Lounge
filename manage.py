#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zenleaf.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Run `python bootstrap.py` first, then use the Python inside .venv "
            "(see the README's Quick Start)."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
