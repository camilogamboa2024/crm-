"""
ASGI config for gamboa_project.

This file exposes the ASGI callable as a module-level variable named ``application``.
It allows asynchronous servers to serve the Django application.
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application  # type: ignore


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gamboa_project.settings')

application = get_asgi_application()
