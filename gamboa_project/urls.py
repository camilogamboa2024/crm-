from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from crm.views import home_view, search_view

urlpatterns = [
    path("", home_view, name="home"),
    path("buscar/", search_view, name="search"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("crm/", include("crm.urls")),
    path("contrato/", TemplateView.as_view(template_name="contract.html"), name="contract"),
    path("admin/", admin.site.urls),
]
