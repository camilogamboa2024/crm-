"""
Django admin customizations for the CRM app.

Registering models here makes them available through Django’s admin interface,
allowing staff to perform CRUD operations via the built‑in interface.
"""

from __future__ import annotations

from django.contrib import admin

from .models import Car, Customer, Reservation


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'license_plate', 'status', 'daily_rate')
    search_fields = ('make', 'model', 'license_plate')
    list_filter = ('status', 'year')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email', 'phone')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'car', 'start_date', 'end_date', 'status', 'total_cost')
    list_filter = ('status',)
    search_fields = ('customer__first_name', 'customer__last_name', 'car__license_plate')
