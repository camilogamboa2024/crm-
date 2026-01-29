"""
Django admin customizations for the CRM app.

Registering models here makes them available through Django’s admin interface,
allowing staff to perform CRUD operations via the built‑in interface.
"""

from __future__ import annotations

from django.contrib import admin

from .models import Car, Customer, Reservation


class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 0
    fields = ("car", "start_date", "end_date", "status", "total_cost")
    readonly_fields = ("total_cost",)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'license_plate', 'status', 'daily_rate', 'updated_at')
    search_fields = ('make', 'model', 'license_plate')
    list_filter = ('status', 'year')
    inlines = (ReservationInline,)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'updated_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    inlines = (ReservationInline,)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'car', 'start_date', 'end_date', 'status', 'total_cost', 'updated_at')
    list_filter = ('status', 'start_date')
    search_fields = ('customer__first_name', 'customer__last_name', 'car__license_plate')
