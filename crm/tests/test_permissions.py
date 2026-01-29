from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class StaffAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.viewer_group, _ = Group.objects.get_or_create(name="viewer")
        self.staff_group, _ = Group.objects.get_or_create(name="staff")

    def test_crm_root_redirects_for_anonymous(self):
        response = self.client.get(reverse("crm:root"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_crm_root_denies_non_staff(self):
        user = self.user_model.objects.create_user(
            username="agent",
            email="agent@example.com",
            password="testpass123",
            is_staff=False,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("crm:root"))
        self.assertEqual(response.status_code, 403)

    def test_crm_root_allows_viewer(self):
        user = self.user_model.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="testpass123",
            is_staff=False,
        )
        user.groups.add(self.viewer_group)
        self.client.force_login(user)
        response = self.client.get(reverse("crm:root"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_create_views(self):
        user = self.user_model.objects.create_user(
            username="viewer2",
            email="viewer2@example.com",
            password="testpass123",
            is_staff=False,
        )
        user.groups.add(self.viewer_group)
        self.client.force_login(user)

        response = self.client.get(reverse("crm:car_add"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("crm:customer_add"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("crm:reservation_add"))
        self.assertEqual(response.status_code, 403)

    def test_crm_root_allows_staff(self):
        user = self.user_model.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        user.groups.add(self.staff_group)
        self.client.force_login(user)
        response = self.client.get(reverse("crm:root"), follow=True)
        self.assertEqual(response.status_code, 200)
