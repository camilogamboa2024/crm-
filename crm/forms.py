"""
Forms for the CRM application.

Using Django’s ModelForm facility we generate forms tied to the underlying
models. These forms automatically include validation logic and are
used in the class‑based views.
"""

from __future__ import annotations

from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from .models import Car, Customer, Reservation


class CarForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Car
        fields = ['make', 'model', 'year', 'license_plate', 'status', 'daily_rate', 'color']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 1900, 'max': 2100}),
            'daily_rate': forms.NumberInput(attrs={'step': '0.01'}),
        }


class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']


class ReservationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Reservation
        fields = ['customer', 'car', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PublicReservationForm(forms.Form):
    """Form used on the public website to allow customers to request a booking."""

    car = forms.ModelChoiceField(
        queryset=Car.objects.none(),
        label='Vehículo',
        help_text='Seleccione el vehículo que desea reservar',
    )
    start_date = forms.DateField(
        label='Fecha de inicio',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        label='Fecha de fin',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    first_name = forms.CharField(max_length=50, label='Nombre')
    last_name = forms.CharField(max_length=50, label='Apellido')
    email = forms.EmailField(label='Correo electrónico')
    phone = forms.CharField(max_length=20, label='Teléfono')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        start_value = self.data.get('start_date') or self.initial.get('start_date')
        end_value = self.data.get('end_date') or self.initial.get('end_date')

        start_date = None
        end_date = None

        try:
            if start_value:
                start_date = date.fromisoformat(str(start_value))
            if end_value:
                end_date = date.fromisoformat(str(end_value))
        except ValueError:
            start_date = None
            end_date = None

        queryset = Car.objects.exclude(status='maintenance')
        if start_date and end_date and end_date >= start_date:
            conflicting_ids = Reservation.conflicting_car_ids(start_date, end_date)
            queryset = queryset.exclude(id__in=conflicting_ids)

        self.fields['car'].queryset = queryset
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.Select, forms.DateInput, forms.TextInput, forms.EmailInput)):
                field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if not start_date or not end_date:
            raise forms.ValidationError("Debes seleccionar fechas de inicio y fin.")
        try:
            Reservation.validate_dates(start_date, end_date, allow_past=False)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

        car = cleaned_data.get("car")
        if car:
            try:
                Reservation.validate_availability(
                    car=car,
                    start_date=start_date,
                    end_date=end_date,
                )
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages) from exc
        return cleaned_data
