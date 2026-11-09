from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="verify_email"),
    path("auth/resend-verification/", views.ResendVerificationView.as_view(), name="resend_verification"),
    path("auth/token/", views.LoginView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/password-reset/", views.PasswordResetRequestView.as_view(), name="password_reset"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("users/me/", views.MeView.as_view(), name="me"),
    path("users/me/roles/", views.RolesView.as_view(), name="my_roles"),
]
