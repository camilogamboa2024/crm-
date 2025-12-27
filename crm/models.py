"""
Data models for the car rental CRM.

This module defines the core entities of the system—cars, customers and
reservations—and their relationships. Each model encapsulates its
domain logic; for example, reservations automatically compute the
total cost based on the car’s daily rate and the number of days
booked.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import models


class Car(models.Model):
    """Represents a vehicle available for rent."""

    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('reserved', 'Reservado'),
        ('rented', 'En uso'),
        ('maintenance', 'Mantenimiento'),
    ]

    make = models.CharField(max_length=50, verbose_name='Marca')
    model = models.CharField(max_length=50, verbose_name='Modelo')
    year = models.PositiveIntegerField(verbose_name='Año')
    license_plate = models.CharField(max_length=20, unique=True, verbose_name='Placa')
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='available', verbose_name='Estado'
    )
    daily_rate = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Tarifa diaria', help_text='Precio por día'
    )
    # Colour of the vehicle (e.g. blanco, gris, plata).
    color = models.CharField(max_length=30, verbose_name='Color')

    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['make', 'model']

    def __str__(self) -> str:
        """Return a human‑readable representation of the car."""
        return f"{self.make} {self.model} {self.color} - {self.license_plate}"


class Customer(models.Model):
    """Represents a customer renting vehicles."""

    first_name = models.CharField(max_length=50, verbose_name='Nombre')
    last_name = models.CharField(max_length=50, verbose_name='Apellido')
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    phone = models.CharField(max_length=20, verbose_name='Teléfono')
    address = models.CharField(max_length=255, blank=True, verbose_name='Dirección')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Reservation(models.Model):
    """Represents a booking of a car by a customer."""

    STATUS_CHOICES = [
        ('booked', 'Reservado'),
        ('in_progress', 'En curso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='Cliente')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, verbose_name='Vehículo')
    start_date = models.DateField(verbose_name='Fecha de inicio')
    end_date = models.DateField(verbose_name='Fecha de fin')
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='booked', verbose_name='Estado'
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False, verbose_name='Costo total'
    )

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-start_date']

    def __str__(self) -> str:
        return f"{self.customer} - {self.car} ({self.start_date} - {self.end_date})"

    def clean(self) -> None:
        """Custom validation for reservations."""
        # Ensure the end date is not before the start date
        if self.end_date < self.start_date:
            raise models.ValidationError('La fecha de fin no puede ser anterior a la de inicio.')
        # Ensure no overlapping reservations for the same car (excluding self)
        conflict = Reservation.objects.filter(
            car=self.car,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(pk=self.pk).exists()
        if conflict:
            raise models.ValidationError('El vehículo ya tiene una reserva en el rango seleccionado.')

    def save(self, *args, **kwargs) -> None:
        """Compute total cost before saving."""
        # Compute number of rental days (inclusive)
        days = (self.end_date - self.start_date).days + 1
        daily_rate: Decimal = self.car.daily_rate  # type: ignore
        self.total_cost = daily_rate * Decimal(days)
        super().save(*args, **kwargs)