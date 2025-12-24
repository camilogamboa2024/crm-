"""
Application configuration for the CRM app. Declares the default app
configuration used by Django when the application is installed.
"""

from __future__ import annotations

from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = 'Gestión de Reservas'
