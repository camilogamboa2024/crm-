"""
WSGI config for gamboa_project.

This file exposes the WSGI callable as a module-level variable named ``application``.
It enables the application to be served via WSGI servers such as Gunicorn.
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application  # type: ignore


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gamboa_project.settings')

application = get_wsgi_application()
