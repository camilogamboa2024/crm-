from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

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
        reservation = Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
            status="booked",
        )
        self.assertEqual(reservation.total_cost, Decimal("300.00"))

    def test_reservation_overlap_is_blocked(self):
        Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 12),
            status="booked",
        )
        conflicting = Reservation(
            customer=self.customer,
            car=self.car,
            start_date=date(2024, 1, 11),
            end_date=date(2024, 1, 15),
            status="booked",
        )
        with self.assertRaises(ValidationError):
            conflicting.full_clean()

    def test_public_reservation_rechecks_overlap(self):
        Reservation.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 3),
            status="booked",
        )
        with self.assertRaises(ValueError):
            _create_public_reservation(
                car_id=self.car.id,
                first_name="Luis",
                last_name="Gomez",
                email="luis@example.com",
                phone="555-0202",
                start_date=date(2024, 2, 2),
                end_date=date(2024, 2, 4),
            )
