#!/usr/bin/env python3
"""
This script is the entry point for Django’s administrative tasks.

It configures the settings module and delegates the management command
to Django’s command‑line utility. Running this file with appropriate
arguments allows you to perform administrative actions like running
the development server, applying migrations, or creating database
superusers.
"""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gamboa_project.settings')
    try:
        from django.core.management import execute_from_command_line  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()