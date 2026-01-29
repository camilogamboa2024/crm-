
"""
crm.views

Vistas del CRM y de la web pública.
"""

from __future__ import annotations

import csv
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMessage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView, View

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ✅ django-ratelimit expone django_ratelimit.decorators (no "ratelimit.decorators")
from django_ratelimit.decorators import ratelimit

from .forms import CarForm, CustomerForm, PublicReservationForm, ReservationForm
from .models import Car, Customer, Reservation


# -----------------------------------------------------------------------------
# CRM (panel de administración)
# -----------------------------------------------------------------------------

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLE_VIEWER = "viewer"


def _user_in_group(user, group_name: str) -> bool:
    return bool(user and user.groups.filter(name=group_name).exists())


def _user_role(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or _user_in_group(user, ROLE_ADMIN):
        return ROLE_ADMIN
    if _user_in_group(user, ROLE_STAFF) or user.is_staff:
        return ROLE_STAFF
    if _user_in_group(user, ROLE_VIEWER):
        return ROLE_VIEWER
    return None


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True
    required_roles: tuple[str, ...] = ()

    def test_func(self) -> bool:
        role = _user_role(self.request.user)
        if role is None:
            return False
        if not self.required_roles:
            return True
        return role in self.required_roles

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = _user_role(self.request.user)
        querystring = self.request.GET.copy()
        querystring.pop("page", None)
        context["user_role"] = role
        context["is_admin"] = role == ROLE_ADMIN
        context["is_staff_role"] = role in {ROLE_ADMIN, ROLE_STAFF}
        context["is_viewer"] = role == ROLE_VIEWER
        context["querystring"] = querystring.urlencode()
        return context


class DashboardView(RoleRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"
    required_roles = (ROLE_ADMIN,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        month_end_day = monthrange(today.year, today.month)[1]
        month_start = today.replace(day=1)
        month_end = today.replace(day=month_end_day)

        revenue_month = Reservation.objects.filter(
            status="completed",
            start_date__range=(month_start, month_end),
        ).aggregate(
            total=Coalesce(
                Sum("total_cost"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        reservations_active = Reservation.objects.filter(status="in_progress").count()
        fleet_available = Car.objects.exclude(status="maintenance").count()

        deliveries_today = Reservation.objects.filter(
            status="booked",
            start_date=today,
        ).count()

        latest_reservations = Reservation.objects.select_related("car", "customer").order_by(
            "-start_date"
        )[:5]

        days_back = 7
        start_window = today - timedelta(days=days_back - 1)
        reservations_by_day = (
            Reservation.objects.filter(start_date__range=(start_window, today))
            .exclude(status="cancelled")
            .values("start_date")
            .annotate(total=Count("id"))
        )
        counts_by_day = {item["start_date"]: item["total"] for item in reservations_by_day}
        chart_labels = []
        chart_values = []
        for offset in range(days_back):
            current = start_window + timedelta(days=offset)
            chart_labels.append(current.strftime("%d/%m"))
            chart_values.append(int(counts_by_day.get(current, 0)))

        context.update(
            {
                "today": today,
                "revenue_month": revenue_month,
                "reservations_active": reservations_active,
                "available_today": fleet_available,
                "deliveries_today": deliveries_today,
                "latest_reservations": latest_reservations,
                "chart_labels": json.dumps(chart_labels),
                "chart_values": json.dumps(chart_values),
            }
        )
        return context


class CarListView(RoleRequiredMixin, ListView):
    model = Car
    template_name = "crm/car_list.html"
    context_object_name = "cars"
    paginate_by = 10
    required_roles = (ROLE_ADMIN, ROLE_STAFF, ROLE_VIEWER)

    def get_queryset(self):
        queryset = super().get_queryset()
        query = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(make__icontains=query)
                | Q(model__icontains=query)
                | Q(license_plate__icontains=query)
                | Q(color__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        context["status"] = (self.request.GET.get("status") or "").strip()
        context["status_choices"] = Car.STATUS_CHOICES
        return context


class CarCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo agregado correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


class CarUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "crm/car_form.html"
    success_url = reverse_lazy("crm:car_list")
    success_message = "Vehículo actualizado correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


class CustomerListView(RoleRequiredMixin, ListView):
    model = Customer
    template_name = "crm/customer_list.html"
    context_object_name = "customers"
    paginate_by = 10
    required_roles = (ROLE_ADMIN, ROLE_STAFF, ROLE_VIEWER)

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


class CustomerCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente agregado correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


class CustomerUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "crm/customer_form.html"
    success_url = reverse_lazy("crm:customer_list")
    success_message = "Cliente actualizado correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


class ReservationListView(RoleRequiredMixin, ListView):
    model = Reservation
    template_name = "crm/reservation_list.html"
    context_object_name = "reservations"
    paginate_by = 10
    required_roles = (ROLE_ADMIN, ROLE_STAFF, ROLE_VIEWER)

    def get_queryset(self):
        queryset = super().get_queryset().select_related("car", "customer")
        query = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        start_date = _parse_iso_date(self.request.GET.get("start_date"))
        end_date = _parse_iso_date(self.request.GET.get("end_date"))
        if query:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=query)
                | Q(customer__last_name__icontains=query)
                | Q(customer__email__icontains=query)
                | Q(car__make__icontains=query)
                | Q(car__model__icontains=query)
                | Q(car__license_plate__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = (self.request.GET.get("q") or "").strip()
        context["status"] = (self.request.GET.get("status") or "").strip()
        context["start_date"] = self.request.GET.get("start_date") or ""
        context["end_date"] = self.request.GET.get("end_date") or ""
        context["status_choices"] = Reservation.STATUS_CHOICES
        return context


class ReservationCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva registrada correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)

    def form_valid(self, form):
        response = super().form_valid(form)
        _send_reservation_confirmation(self.object)
        return response


class ReservationUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = "crm/reservation_form.html"
    success_url = reverse_lazy("crm:reservation_list")
    success_message = "Reserva actualizada correctamente."
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


def crm_root(request):
    """/crm/ -> redirige según rol."""
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    role = _user_role(request.user)
    if role is None:
        raise PermissionDenied
    if role == ROLE_ADMIN:
        return redirect("crm:dashboard")
    return redirect("crm:reservation_list")


class ReservationContractView(RoleRequiredMixin, View):
    required_roles = (ROLE_ADMIN, ROLE_STAFF)

    def get(self, request, pk):
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer", "car"),
            pk=pk,
        )
        pdf_bytes = _render_contract_pdf(reservation)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="reserva-{reservation.id}.pdf"'
        return response


class CalendarView(RoleRequiredMixin, TemplateView):
    template_name = "crm/calendar.html"
    required_roles = (ROLE_ADMIN, ROLE_STAFF)


def reservation_events_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    role = _user_role(request.user)
    if role not in {ROLE_ADMIN, ROLE_STAFF}:
        raise PermissionDenied
    events = []
    reservations = Reservation.objects.select_related("car", "customer").exclude(status="cancelled")
    color_map = {
        "booked": "#3699ff",
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


class ExportReservationsCsvView(RoleRequiredMixin, View):
    required_roles = (ROLE_ADMIN, ROLE_STAFF)

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
    return Reservation.conflicting_car_ids(start_date, end_date)


def _serialize_cars(qs):
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
                "image_url": "/static/custom/images/car_placeholder.png",
                "category": "SUV" if (car.model or "").lower() in {"sonet"} else "HATCHBACK",
                "status": car.status,
            }
        )
    return out


def _render_contract_pdf(reservation: Reservation) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - inch
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(inch, y, f"Contrato de Reserva #{reservation.id}")

    y -= 0.5 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(inch, y, "Datos del cliente")
    pdf.setFont("Helvetica", 11)
    y -= 0.25 * inch
    pdf.drawString(inch, y, f"Nombre: {reservation.customer.first_name} {reservation.customer.last_name}")
    y -= 0.2 * inch
    pdf.drawString(inch, y, f"Email: {reservation.customer.email}")
    y -= 0.2 * inch
    pdf.drawString(inch, y, f"Teléfono: {reservation.customer.phone}")

    y -= 0.45 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(inch, y, "Datos del vehículo")
    pdf.setFont("Helvetica", 11)
    y -= 0.25 * inch
    pdf.drawString(inch, y, f"Vehículo: {reservation.car.make} {reservation.car.model} {reservation.car.year}")
    y -= 0.2 * inch
    pdf.drawString(inch, y, f"Placa: {reservation.car.license_plate}")
    y -= 0.2 * inch
    pdf.drawString(inch, y, f"Color: {reservation.car.color}")

    y -= 0.45 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(inch, y, "Fechas de la reserva")
    pdf.setFont("Helvetica", 11)
    y -= 0.25 * inch
    pdf.drawString(inch, y, f"Inicio: {reservation.start_date:%d/%m/%Y}")
    y -= 0.2 * inch
    pdf.drawString(inch, y, f"Fin: {reservation.end_date:%d/%m/%Y}")

    y -= 0.45 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(inch, y, "Desglose de costos")
    pdf.setFont("Helvetica", 11)
    y -= 0.25 * inch
    pdf.drawString(inch, y, f"Total reserva: ${reservation.total_cost}")
    y -= 0.2 * inch
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(inch, y, f"Total a pagar: ${reservation.total_cost}")

    y -= 0.6 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(inch, y, "Firma del cliente:")
    y -= 0.2 * inch
    pdf.line(inch, y, inch + 3.5 * inch, y)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _send_reservation_confirmation(reservation: Reservation) -> None:
    try:
        pdf_bytes = _render_contract_pdf(reservation)
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
    with transaction.atomic():
        car = get_object_or_404(Car.objects.select_for_update(), id=car_id)
        try:
            Reservation.validate_dates(start_date, end_date, allow_past=False)
            Reservation.validate_availability(
                car=car,
                start_date=start_date,
                end_date=end_date,
            )
        except ValidationError as exc:
            raise ValueError(exc.messages[0]) from exc

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
# Web pública (Actualizado para home.html y search.html)
# -----------------------------------------------------------------------------

def home_view(request):
    """
    Home page. Renderiza 'home.html' con la lista completa de vehículos
    para la sección 'Nuestra Flota'.
    """
    cars = Car.objects.all().order_by("make", "model", "year")
    return render(request, "home.html", {"cars": cars})


@ratelimit(key="ip", rate="60/m", method="GET", block=True)
def search_view(request):
    """
    Página de búsqueda y filtros. Soporta filtrar por ID de vehículo
    (para cuando el usuario viene del Home), además de fechas, marca y precio.
    """
    pickup = (request.GET.get("pickup") or "").strip()

    start_raw = request.GET.get("start_date") or ""
    end_raw = request.GET.get("end_date") or ""

    start_date = _parse_iso_date(start_raw)
    end_date = _parse_iso_date(end_raw)

    selected_makes = request.GET.getlist("make")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")

    # Nuevo: Filtro por ID (enlace directo desde el home)
    car_id = request.GET.get("car_id")

    qs = Car.objects.exclude(status="maintenance")

    days = None
    if start_date and end_date and end_date >= start_date:
        days = (end_date - start_date).days + 1
        # Excluir autos ocupados en esas fechas
        qs = qs.exclude(id__in=_conflicting_car_ids(start_date, end_date))

    # Si viene un car_id, filtramos para mostrar solo ese (flow "Reservar" desde Home)
    if car_id:
        qs = qs.filter(id=car_id)

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

    qs = qs.order_by("make", "model", "year")
    cars = list(qs)

    # Calcular precio total si hay días seleccionados
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


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="dispatch")
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
        pickup = self.request.GET.get("pickup") or self.request.POST.get("pickup") or ""

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


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
@require_POST
def public_reservation_api(request):
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
