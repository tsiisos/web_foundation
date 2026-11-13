import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()

PASSWORD = "S3cure-pass-phrase!"
NEW_PASSWORD = "An0ther-strong-phrase!"
LINK_RE = re.compile(r"uid=([^&\s]+)&token=(\S+)")


class SessionSecurityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("owner@example.com", PASSWORD, is_email_verified=True)

    def login(self, password=PASSWORD):
        res = self.client.post(
            "/api/v1/auth/token/", {"email": "owner@example.com", "password": password}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        return res.data

    def refresh(self, token):
        return self.client.post("/api/v1/auth/token/refresh/", {"refresh": token}, format="json")

    def authenticate(self, tokens):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    # ---- logout ----

    def test_logout_revokes_the_refresh_token(self):
        tokens = self.login()
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 200)
        res = self.client.post("/api/v1/auth/token/blacklist/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    # ---- password change ----

    def test_password_change_requires_the_current_password(self):
        self.authenticate(self.login())
        res = self.client.post(
            "/api/v1/users/me/password/",
            {"current_password": "wrong", "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_password_change_rejects_a_weak_password(self):
        self.authenticate(self.login())
        res = self.client.post(
            "/api/v1/users/me/password/",
            {"current_password": PASSWORD, "new_password": "12345678"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_password_change_requires_authentication(self):
        res = self.client.post(
            "/api/v1/users/me/password/",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

    def test_password_change_revokes_every_session(self):
        tokens = self.login()
        other_device = self.login()
        self.authenticate(tokens)
        res = self.client.post(
            "/api/v1/users/me/password/",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.client.credentials()
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)
        self.assertEqual(self.refresh(other_device["refresh"]).status_code, 401)
        self.login(password=NEW_PASSWORD)  # the new password works

    # ---- password reset ----

    def test_password_reset_revokes_every_session(self):
        tokens = self.login()
        res = self.client.post("/api/v1/auth/password-reset/", {"email": "owner@example.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        uid, token = LINK_RE.search(mail.outbox[0].body).groups()
        res = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    # ---- account deletion ----

    def test_delete_account_requires_the_password(self):
        self.authenticate(self.login())
        res = self.client.post("/api/v1/users/me/delete/", {"password": "wrong"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.filter(email="owner@example.com").exists())

    def test_delete_account_removes_the_user_and_ends_sessions(self):
        tokens = self.login()
        self.authenticate(tokens)
        res = self.client.post("/api/v1/users/me/delete/", {"password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(email="owner@example.com").exists())
        self.client.credentials()
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    def test_staff_accounts_cannot_be_deleted_through_the_api(self):
        User.objects.create_user("staff@example.com", PASSWORD, is_staff=True, is_email_verified=True)
        res = self.client.post(
            "/api/v1/auth/token/", {"email": "staff@example.com", "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        res = self.client.post("/api/v1/users/me/delete/", {"password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(User.objects.filter(email="staff@example.com").exists())
