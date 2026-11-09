import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()

PASSWORD = "S3cure-pass-phrase!"
LINK_RE = re.compile(r"uid=([^&\s]+)&token=(\S+)")


class AuthFlowTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters between tests

    def register(self, email="Test@Example.com", **extra):
        data = {"email": email, "password": PASSWORD, "first_name": "Test", "last_name": "User"}
        data.update(extra)
        return self.client.post("/api/v1/auth/register/", data, format="json")

    def login(self, email="test@example.com", password=PASSWORD):
        return self.client.post("/api/v1/auth/token/", {"email": email, "password": password}, format="json")

    def authenticate(self):
        self.register()
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_register_creates_unverified_customer_and_sends_email(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("password", res.data)
        user = User.objects.get(email="test@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_provider)
        self.assertEqual(len(mail.outbox), 1)

    def test_register_as_both_customer_and_provider(self):
        res = self.register(is_customer=True, is_provider=True)
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="test@example.com")
        self.assertTrue(user.is_customer and user.is_provider)

    def test_register_rejects_no_role(self):
        res = self.register(is_customer=False, is_provider=False)
        self.assertEqual(res.status_code, 400)

    def test_register_cannot_grant_staff(self):
        res = self.register(is_staff=True, is_superuser=True)
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="test@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_register_rejects_weak_password(self):
        res = self.client.post(
            "/api/v1/auth/register/", {"email": "weak@example.com", "password": "12345678"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_register_rejects_duplicate_email_in_any_case(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register(email="TEST@EXAMPLE.COM").status_code, 400)

    def test_login_is_case_insensitive(self):
        self.register()
        res = self.login(email="TEST@EXAMPLE.COM")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_verify_email_flow(self):
        self.register()
        uid, token = LINK_RE.search(mail.outbox[0].body).groups()
        res = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(User.objects.get(email="test@example.com").is_email_verified)
        # the link cannot be used twice
        res = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 401)

    def test_me_updates_profile_but_not_roles(self):
        self.authenticate()
        res = self.client.get("/api/v1/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], "test@example.com")
        res = self.client.patch(
            "/api/v1/users/me/", {"first_name": "Changed", "is_provider": True}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["first_name"], "Changed")
        self.assertFalse(res.data["is_provider"])

    def test_roles_endpoint_adds_provider_role(self):
        self.authenticate()
        res = self.client.patch("/api/v1/users/me/roles/", {"is_provider": True}, format="json")
        self.assertEqual(res.status_code, 200)
        user = User.objects.get(email="test@example.com")
        self.assertTrue(user.is_customer and user.is_provider)

    def test_roles_endpoint_rejects_turning_off_every_role(self):
        self.authenticate()
        res = self.client.patch("/api/v1/users/me/roles/", {"is_customer": False}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.get(email="test@example.com").is_customer)

    def test_roles_endpoint_requires_authentication(self):
        res = self.client.patch("/api/v1/users/me/roles/", {"is_provider": True}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_password_reset_flow(self):
        self.register()
        mail.outbox.clear()
        res = self.client.post("/api/v1/auth/password-reset/", {"email": "TEST@example.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        uid, token = LINK_RE.search(mail.outbox[0].body).groups()
        new_password = "An0ther-strong-phrase!"
        res = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": new_password},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.login(password=new_password).status_code, 200)
        self.assertEqual(self.login().status_code, 401)

    def test_password_reset_for_unknown_email_sends_nothing(self):
        res = self.client.post("/api/v1/auth/password-reset/", {"email": "nobody@example.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_rejects_bad_token(self):
        self.register()
        uid, _ = LINK_RE.search(mail.outbox[0].body).groups()
        res = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": "bad-token", "new_password": "An0ther-strong-phrase!"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
