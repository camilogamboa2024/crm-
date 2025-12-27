from __future__ import annotations

from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("", views.crm_root, name="root"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),

    path("cars/", views.CarListView.as_view(), name="car_list"),
    path("cars/add/", views.CarCreateView.as_view(), name="car_add"),
    path("cars/<int:pk>/edit/", views.CarUpdateView.as_view(), name="car_edit"),

    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/add/", views.CustomerCreateView.as_view(), name="customer_add"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer_edit"),

    path("reservations/", views.ReservationListView.as_view(), name="reservation_list"),
    path("reservations/add/", views.ReservationCreateView.as_view(), name="reservation_add"),
    path("reservations/<int:pk>/edit/", views.ReservationUpdateView.as_view(), name="reservation_edit"),

    # ✅ checkout público
    path("public/reserve/", views.PublicReservationView.as_view(), name="public_reservation"),
    path("public/reserve/success/", views.public_reservation_success_view, name="public_reservation_success"),
]