"""
crm.views

Vistas del CRM y de la web pública.
"""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import csv

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView, View
from xhtml2pdf import pisa

from .forms import CarForm, CustomerForm, PublicReservationForm, ReservationForm
from .models import Car, Customer, Reservation


# -----------------------------------------------------------------------------
# CRM (panel)
# -----------------------------------------------------------------------------


def _is_manager(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name="Gerencia").exists()


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_staff)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_manager"] = _is_manager(self.request.user)
        return context


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not _is_manager(request.user):
            return redirect("crm:reservation_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        month_end_day = monthrange(today.year, today.month)[1]
        month_start = today.replace(day=1)
        month_end = today.replace(day=month_end_day)

        revenue_month = (
            Reservation.objects.filter(start_date__range=(month_start, month_end))
            .exclude(status="cancelled")
            .aggregate(
                total=Coalesce(
                    Sum("total_cost"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["total"]
        )

        reservations_month = Reservation.objects.filter(
            start_date__range=(month_start, month_end)
        ).exclude(status="cancelled").count()

        cancelled_month = Reservation.objects.filter(
            status="cancelled",
            start_date__range=(month_start, month_end),
        ).count()

        available_today = (
            Car.objects.filter(status="available")
            .exclude(id__in=_conflicting_car_ids(today, today))
            .count()
        )

        latest_reservations = (
            Reservation.objects.select_related("car", "customer")
            .order_by("-start_date")[:5]
        )

        context.update(
            {
                "today": today,
                "revenue_month": revenue_month,
                "reservations_month": reservations_month,
                "available_today": available_today,
                "cancelled_month": cancelled_month,
                "latest_reservations": latest_reservations,
            }
        )
        return context


class CarListView(StaffRequiredMixin, ListView):
    model = Car
    template_name = "crm/car_list.html"
    context_object_name = "cars"

    def get_queryset(self):
        queryset = super().get_queryset()
        query = (self.request.GET.get("q") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(make__icontains=query)
                | Q(model__icontains=query)
                | Q(license_plate__icontains=query)
                | Q(color__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        return context


class CarCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo agregado correctamente."


class CarUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo actualizado correctamente."


class CustomerListView(StaffRequiredMixin, ListView):
    model = Customer
    template_name = "crm/customer_list.html"
    context_object_name = "customers"

    def get_queryset(self):
        queryset = super().get_queryset()
        query = (self.request.GET.get("q") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        return context


class CustomerCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente agregado correctamente."


class CustomerUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente actualizado correctamente."


class ReservationListView(StaffRequiredMixin, ListView):
    model = Reservation
    template_name = "crm/reservation_list.html"
    context_object_name = "reservations"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("car", "customer")
        query = (self.request.GET.get("q") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=query)
                | Q(customer__last_name__icontains=query)
                | Q(customer__email__icontains=query)
                | Q(car__make__icontains=query)
                | Q(car__model__icontains=query)
                | Q(car__license_plate__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        return context


class ReservationCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva registrada correctamente."

    def form_valid(self, form):
        response = super().form_valid(form)
        _send_reservation_confirmation(self.object)
        return response


class ReservationUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva actualizada correctamente."


def crm_root(request):
    """/crm/ -> redirige según rol."""
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    if not request.user.is_staff:
        raise PermissionDenied
    if _is_manager(request.user):
        return redirect("crm:dashboard")
    return redirect("crm:reservation_list")


class ReservationContractView(StaffRequiredMixin, View):
    def get(self, request, pk):
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer", "car"),
            pk=pk,
        )
        template = get_template("crm/reservation_contract.html")
        context = {
            "reservation": reservation,
            "customer": reservation.customer,
            "car": reservation.car,
        }
        html = template.render(context)
        pdf_bytes = _render_contract_pdf(html)
        if pdf_bytes is None:
            return HttpResponse("Error al generar el PDF.", status=500)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="reserva-{reservation.id}.pdf"'
        return response


class CalendarView(StaffRequiredMixin, TemplateView):
    template_name = "crm/calendar.html"


def reservation_events_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if not request.user.is_staff:
        raise PermissionDenied
    events = []
    reservations = Reservation.objects.select_related("car", "customer").exclude(status="cancelled")
    color_map = {
        "booked": "#3699ff",
        "pending": "#3699ff",
        "cancelled": "#f64e60",
        "maintenance": "#ffc107",
        "completed": "#1bc5bd",
        "in_progress": "#0d6efd",
    }
    for reservation in reservations:
        end_date = reservation.end_date + timedelta(days=1)
        color = color_map.get(reservation.status, "#3699ff")
        events.append(
            {
                "title": f"{reservation.car.make} {reservation.car.model} - {reservation.customer}",
                "start": reservation.start_date.isoformat(),
                "end": end_date.isoformat(),
                "backgroundColor": color,
                "borderColor": color,
                "url": reverse("crm:reservation_edit", args=[reservation.id]),
            }
        )
    return JsonResponse(events, safe=False)


class ExportReservationsCsvView(StaffRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="reservas.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Fecha Inicio", "Fecha Fin", "Cliente", "Auto", "Total", "Estado"])
        reservations = Reservation.objects.select_related("customer", "car").order_by("-start_date")
        for reservation in reservations:
            writer.writerow(
                [
                    reservation.id,
                    reservation.start_date,
                    reservation.end_date,
                    str(reservation.customer),
                    str(reservation.car),
                    reservation.total_cost,
                    reservation.get_status_display(),
                ]
            )
        return response


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
        )
        .exclude(status="cancelled")
        .values_list("car_id", flat=True)
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


def _render_contract_pdf(html: str) -> bytes | None:
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    if pisa_status.err:
        return None
    return buffer.getvalue()


def _send_reservation_confirmation(reservation: Reservation) -> None:
    try:
        template = get_template("crm/reservation_contract.html")
        html = template.render(
            {
                "reservation": reservation,
                "customer": reservation.customer,
                "car": reservation.car,
            }
        )
        pdf_bytes = _render_contract_pdf(html)
        if pdf_bytes is None:
            return
        subject = "Reserva Confirmada"
        body = "Gracias por reservar con Gamboa Rental Cars. Adjuntamos el contrato en PDF."
        message = EmailMessage(
            subject=subject,
            body=body,
            to=[reservation.customer.email],
        )
        message.attach(f"reserva-{reservation.id}.pdf", pdf_bytes, "application/pdf")
        message.send(fail_silently=True)
    except Exception:
        return


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

    with transaction.atomic():
        conflict = Reservation.objects.select_for_update().filter(
            car=car,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exclude(status="cancelled").exists()
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
            status="booked",
        )
        return reservation


# -----------------------------------------------------------------------------
# Web pública
# -----------------------------------------------------------------------------


def home_view(request):
    """
    Home sirve la página pública con listado de vehículos.
    """
    cars = Car.objects.all().order_by("make", "model", "year")
    return render(request, "home.html", {"cars": cars})


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
        days = (end_date - start_date).days + 1
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
            delta = (end_date - start_date).days + 1
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

        _send_reservation_confirmation(reservation)
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