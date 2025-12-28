from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class StaffAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_crm_root_redirects_for_anonymous(self):
        response = self.client.get(reverse("crm:root"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

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

    def test_crm_root_allows_staff(self):
        user = self.user_model.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("crm:root"), follow=True)
        self.assertEqual(response.status_code, 200)
