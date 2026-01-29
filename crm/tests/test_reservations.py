from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from crm.models import Car, Customer, Reservation
from crm.views import _create_public_reservation


class ReservationRulesTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            make="Toyota",
            model="Yaris",
            year=2022,
            license_plate="ABC-123",
            status="available",
            daily_rate=Decimal("100.00"),
            color="Rojo",
        )
        self.customer = Customer.objects.create(
            first_name="Ana",
            last_name="Perez",
            email="ana@example.com",
            phone="555-0101",
            address="Calle 1",
        )

    def test_total_cost_is_inclusive_of_end_date(self):
        start_date = timezone.localdate() + timedelta(days=1)
        end_date = start_date + timedelta(days=2)
        reservation = Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=start_date,
            end_date=end_date,
            status="booked",
        )
        self.assertEqual(reservation.total_cost, Decimal("300.00"))

    def test_reservation_overlap_is_blocked(self):
        base_date = timezone.localdate() + timedelta(days=10)
        Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=base_date,
            end_date=base_date + timedelta(days=2),
            status="booked",
        )
        conflicting = Reservation(
            customer=self.customer,
            car=self.car,
            start_date=base_date + timedelta(days=1),
            end_date=base_date + timedelta(days=5),
            status="booked",
        )
        with self.assertRaises(ValidationError):
            conflicting.full_clean()

    def test_reservation_end_date_before_start_date(self):
        base_date = timezone.localdate() + timedelta(days=5)
        reservation = Reservation(
            customer=self.customer,
            car=self.car,
            start_date=base_date,
            end_date=base_date - timedelta(days=4),
            status="booked",
        )
        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_public_reservation_rechecks_overlap(self):
        base_date = timezone.localdate() + timedelta(days=15)
        Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=base_date,
            end_date=base_date + timedelta(days=2),
            status="booked",
        )
        with self.assertRaises(ValueError):
            _create_public_reservation(
                car_id=self.car.id,
                first_name="Luis",
                last_name="Gomez",
                email="luis@example.com",
                phone="555-0202",
                start_date=base_date + timedelta(days=1),
                end_date=base_date + timedelta(days=3),
            )

    def test_public_reservation_reuses_customer(self):
        base_date = timezone.localdate() + timedelta(days=20)
        reservation = _create_public_reservation(
            car_id=self.car.id,
            first_name="Ana",
            last_name="Perez",
            email="ana@example.com",
            phone="555-9999",
            start_date=base_date,
            end_date=base_date + timedelta(days=2),
        )
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertEqual(reservation.customer.email, "ana@example.com")
