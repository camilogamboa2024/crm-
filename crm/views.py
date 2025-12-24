from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from django.views.generic.edit import FormView

from .forms import CarForm, CustomerForm, ReservationForm, PublicReservationForm
from .models import Car, Customer, Reservation


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# -------------------------
# HOME (PUBLIC)
# -------------------------
def home_view(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


# -------------------------
# BUSCAR (PUBLIC)
# -------------------------
def search_view(request: HttpRequest) -> HttpResponse:
    pickup = request.GET.get("pickup", "Panamá")
    start = _parse_iso_date(request.GET.get("start_date"))
    end = _parse_iso_date(request.GET.get("end_date"))

    rental_days = 0
    if start and end and end >= start:
        # Importante: estilo "Multialquileres" (end - start), NO inclusivo
        delta = (end - start).days
        rental_days = max(1, delta)

    cars = Car.objects.filter(status="available").order_by("name")

    cars_payload = []
    for car in cars:
        total = Decimal("0.00")
        if rental_days:
            total = (car.daily_rate or Decimal("0.00")) * Decimal(rental_days)

        cars_payload.append(
            {
                "id": car.id,
                "name": car.name,
                "brand": car.brand,
                "model": car.model,
                "year": car.year,
                "color": car.color,
                "daily_rate": float(car.daily_rate or 0),
                "total": float(_q2(total)),
                "status": car.status,
                "image_url": car.image_url or "",
            }
        )

    context = {
        "cars_json": json.dumps(cars_payload),
        "pickup": pickup,
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
        "rental_days": rental_days,
    }
    return render(request, "search.html", context)


# -------------------------
# CRM ROOT
# -------------------------
@login_required
def crm_root(request: HttpRequest) -> HttpResponse:
    return redirect("crm:car_list")


# -------------------------
# CRUD (CRM)
# -------------------------
class CarListView(LoginRequiredMixin, ListView):
    model = Car
    template_name = "crm/car_list.html"
    context_object_name = "cars"


class CarCreateView(LoginRequiredMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")


class CarUpdateView(LoginRequiredMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "crm/customer_list.html"
    context_object_name = "customers"


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")


class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = "crm/reservation_list.html"
    context_object_name = "reservations"


class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")


class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")


# -------------------------
# ✅ CHECKOUT PUBLICO (ESTILO MULTIALQUILERES)
# -------------------------
class PublicReservationView(FormView):
    # ✅ A) CLAVE: esto quita el "verde" porque ya NO usa public_reservation_form.html
    template_name = "crm/public_checkout.html"
    form_class = PublicReservationForm
    success_url = reverse_lazy("crm:public_reservation_success")

    def get_initial(self):
        initial = super().get_initial()

        car_id = self.request.GET.get("car_id") or self.request.POST.get("car_id")
        start_raw = self.request.GET.get("start_date") or self.request.POST.get("start_date")
        end_raw = self.request.GET.get("end_date") or self.request.POST.get("end_date")

        if car_id and str(car_id).isdigit():
            initial["car"] = int(car_id)

        start = _parse_iso_date(start_raw)
        end = _parse_iso_date(end_raw)
        if start:
            initial["start_date"] = start
        if end:
            initial["end_date"] = end

        return initial

    def get_form(self, form_class=None):
        """
        Para que Bootstrap se vea bien, forzamos class="form-control"
        en los inputs renderizados como {{ form.first_name }}, etc.
        """
        form = super().get_form(form_class)
        for fname in ["first_name", "last_name", "email", "phone"]:
            if fname in form.fields:
                form.fields[fname].widget.attrs.setdefault("class", "form-control")
                form.fields[fname].widget.attrs.setdefault("placeholder", form.fields[fname].label or "")
        return form

    # ✅ B) Contexto tipo Multialquileres (resumen derecha)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        car_id = self.request.GET.get("car_id") or self.request.POST.get("car_id")
        pickup = self.request.GET.get("pickup") or self.request.POST.get("pickup") or "Panamá"

        start_raw = self.request.GET.get("start_date") or self.request.POST.get("start_date")
        end_raw = self.request.GET.get("end_date") or self.request.POST.get("end_date")

        car = None
        start_date = None
        end_date = None

        try:
            if car_id:
                car = Car.objects.filter(pk=car_id).first()
            if start_raw:
                start_date = date.fromisoformat(start_raw)
            if end_raw:
                end_date = date.fromisoformat(end_raw)
        except Exception:
            pass

        rental_days = 0
        daily_rate = Decimal("0.00")
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        total = Decimal("0.00")

        if car and start_date and end_date:
            delta = (end_date - start_date).days
            rental_days = max(1, delta)

            daily_rate = car.daily_rate or Decimal("0.00")
            subtotal = _q2(daily_rate * Decimal(rental_days))
            tax = _q2(subtotal * Decimal("0.07"))
            total = _q2(subtotal + tax)

        ctx.update(
            {
                "car": car,
                "pickup": pickup,
                "start_date": start_date,
                "end_date": end_date,
                "rental_days": rental_days,
                "daily_rate": daily_rate,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
            }
        )
        return ctx

    def form_valid(self, form):
        if not self.request.POST.get("accept_terms"):
            form.add_error(None, "Debes aceptar los Términos y Condiciones.")
            return self.form_invalid(form)

        car = form.cleaned_data["car"]
        start = form.cleaned_data["start_date"]
        end = form.cleaned_data["end_date"]

        # Evitar reservas cruzadas
        if Reservation.objects.filter(
            car=car,
            status__in=["pending", "confirmed"],
            start_date__lt=end,
            end_date__gt=start,
        ).exists():
            form.add_error(None, "Este vehículo ya no está disponible para esas fechas.")
            return self.form_invalid(form)

        customer = Customer.objects.create(
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            phone=form.cleaned_data["phone"],
        )

        reservation = Reservation.objects.create(
            customer=customer,
            car=car,
            start_date=start,
            end_date=end,
            status="pending",
        )

        self.request.session["last_reservation_id"] = reservation.id
        return redirect("crm:public_reservation_success")


def public_reservation_success_view(request: HttpRequest) -> HttpResponse:
    rid = request.session.get("last_reservation_id")
    reservation = None
    if rid:
        reservation = (
            Reservation.objects.select_related("car", "customer")
            .filter(id=rid)
            .first()
        )

    return render(
        request,
        "crm/public_reservation_success.html",
        {"reservation": reservation},
    )
