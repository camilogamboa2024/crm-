"""
crm.views

Vistas del CRM y de la web pública.

Flujo público:
Home -> /buscar (resultados + filtros) -> /crm/public/reserve/ (checkout) -> success
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.messages.views import SuccessMessageMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, FormView, ListView, UpdateView

from .forms import CarForm, CustomerForm, PublicReservationForm, ReservationForm
from .models import Car, Customer, Reservation


# -----------------------------------------------------------------------------
# CRM (panel)
# -----------------------------------------------------------------------------


class CarListView(ListView):
    model = Car
    template_name = "crm/car_list.html"
    context_object_name = "cars"


class CarCreateView(SuccessMessageMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo agregado correctamente."


class CarUpdateView(SuccessMessageMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo actualizado correctamente."


class CustomerListView(ListView):
    model = Customer
    template_name = "crm/customer_list.html"
    context_object_name = "customers"


class CustomerCreateView(SuccessMessageMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente agregado correctamente."


class CustomerUpdateView(SuccessMessageMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente actualizado correctamente."


class ReservationListView(ListView):
    model = Reservation
    template_name = "crm/reservation_list.html"
    context_object_name = "reservations"


class ReservationCreateView(SuccessMessageMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva registrada correctamente."


class ReservationUpdateView(SuccessMessageMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva actualizada correctamente."


def crm_root(request):
    """/crm/ -> redirige al listado de vehículos."""
    return redirect("crm:car_list")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _conflicting_car_ids(start_date: date, end_date: date) -> list[int]:
    """IDs de carros con reservas que se crucen con el rango solicitado."""
    return list(
        Reservation.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).values_list("car_id", flat=True)
    )


def _serialize_cars(qs):
    """Serializa Car queryset a dict listo para JS/React (si lo usas)."""
    out = []
    for car in qs:
        out.append(
            {
                "id": car.id,
                "make": car.make,
                "model": car.model,
                "year": car.year,
                "color": car.color,
                "license_plate": car.license_plate,
                "daily_rate": float(car.daily_rate),
                "name": f"{car.make} {car.model} {car.year}",
                "image_url": "/static/images/car_placeholder.png",
                "category": "SUV" if (car.model or "").lower() in {"sonet"} else "HATCHBACK",
                "status": car.status,
            }
        )
    return out


def _create_public_reservation(
    *,
    car_id: int,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    start_date: date,
    end_date: date,
) -> Reservation:
    """Crea Customer + Reservation validando conflicto."""
    if end_date < start_date:
        raise ValueError("Rango de fechas inválido.")

    car = get_object_or_404(Car, id=car_id)

    conflict = Reservation.objects.filter(
        car=car,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if conflict:
        raise ValueError("El vehículo no está disponible en ese rango.")

    customer, _ = Customer.objects.get_or_create(
        email=email,
        defaults={"first_name": first_name, "last_name": last_name, "phone": phone},
    )
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.save()

    reservation = Reservation.objects.create(
        car=car,
        customer=customer,
        start_date=start_date,
        end_date=end_date,
        status="pending",
    )
    return reservation


# -----------------------------------------------------------------------------
# Web pública
# -----------------------------------------------------------------------------


def home_view(request):
    """
Home puede seguir como está. Entregamos cars_json por si home.html lo usa.
"""
    cars_json = json.dumps(
        _serialize_cars(Car.objects.all().order_by("make", "model", "year")),
        cls=DjangoJSONEncoder,
    )
    return render(request, "home.html", {"cars": cars_json})


def search_view(request):
    """
/buscar -> resultados server-side (para evitar pantallazo blanco si falla JS)
"""
    pickup = (request.GET.get("pickup") or "Panamá").strip()

    start_raw = request.GET.get("start_date") or ""
    end_raw = request.GET.get("end_date") or ""

    start_date = _parse_iso_date(start_raw)
    end_date = _parse_iso_date(end_raw)

    selected_makes = request.GET.getlist("make")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")

    qs = Car.objects.filter(status="available")

    days = None
    if start_date and end_date and end_date >= start_date:
        days = (end_date - start_date).days
        if days == 0:
            days = 1
        qs = qs.exclude(id__in=_conflicting_car_ids(start_date, end_date))

    if selected_makes:
        qs = qs.filter(make__in=selected_makes)

    try:
        if min_price != "":
            qs = qs.filter(daily_rate__gte=float(min_price))
    except ValueError:
        min_price = ""

    try:
        if max_price != "":
            qs = qs.filter(daily_rate__lte=float(max_price))
    except ValueError:
        max_price = ""

    # ✅ CLAVE: ordenar por campos reales del modelo (NO "name")
    qs = qs.order_by("make", "model", "year")

    cars = list(qs)

    if days:
        for c in cars:
            c.total_price = round(float(c.daily_rate) * days, 2)

    makes = list(Car.objects.order_by("make").values_list("make", flat=True).distinct())

    cars_json = json.dumps(_serialize_cars(qs), cls=DjangoJSONEncoder)
    query_json = json.dumps(
        {"pickup": pickup, "start_date": start_raw, "end_date": end_raw, "days": days},
        cls=DjangoJSONEncoder,
    )

    context = {
        "pickup": pickup,
        "start_date": start_raw,
        "end_date": end_raw,
        "days": days,
        "cars": cars,
        "makes": makes,
        "selected_makes": selected_makes,
        "min_price": min_price,
        "max_price": max_price,
        "cars_json": cars_json,
        "query_json": query_json,
    }
    return render(request, "search.html", context)


class PublicReservationView(FormView):
    form_class = PublicReservationForm
    template_name = "crm/public_checkout.html"
    success_url = reverse_lazy("crm:public_reservation_success")

    def get_initial(self):
        initial = super().get_initial()
        car_id = self.request.GET.get("car_id")
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")

        if car_id:
            initial["car"] = car_id
        if start_date:
            initial["start_date"] = start_date
        if end_date:
            initial["end_date"] = end_date

        return initial

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

            daily_rate = (car.daily_rate or Decimal("0.00"))
            subtotal = (daily_rate * Decimal(rental_days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tax = (subtotal * Decimal("0.07")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total = (subtotal + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
        # checkbox del template (no está en el form)
        if not self.request.POST.get("accept_terms"):
            form.add_error(None, "Debes aceptar los Términos y condiciones.")
            return self.form_invalid(form)

        car = form.cleaned_data["car"]
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        first_name = form.cleaned_data["first_name"]
        last_name = form.cleaned_data["last_name"]
        email = form.cleaned_data["email"]
        phone = form.cleaned_data["phone"]

        try:
            reservation = _create_public_reservation(
                car_id=car.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

        return redirect(f"{self.success_url}?rid={reservation.id}")


def public_reservation_success_view(request):
    rid = request.GET.get("rid")
    reservation = (
        Reservation.objects.filter(id=rid)
        .select_related("car", "customer")
        .first()
    )
    return render(request, "crm/public_reservation_success.html", {"reservation": reservation})


@require_POST
def public_reservation_api(request):
    """Endpoint JSON opcional (si luego usas React/JS)."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    try:
        car_id = int(payload.get("car_id"))
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        email = (payload.get("email") or "").strip()
        phone = (payload.get("phone") or "").strip()
        start_date = date.fromisoformat(payload.get("start_date"))
        end_date = date.fromisoformat(payload.get("end_date"))

        reservation = _create_public_reservation(
            car_id=car_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            start_date=start_date,
            end_date=end_date,
        )
        return JsonResponse({"ok": True, "reservation_id": reservation.id})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
