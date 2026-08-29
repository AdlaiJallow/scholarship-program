from django.urls import path

from . import views

urlpatterns = [
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/activation/verify-identity", views.VerifyIdentityView.as_view(), name="auth-activation-verify-identity"),
    path("auth/activation/verify-code", views.VerifyCodeView.as_view(), name="auth-activation-verify-code"),
    path("auth/activation/resend-code", views.ResendCodeView.as_view(), name="auth-activation-resend-code"),
    path("auth/activation/create-account", views.CreateAccountView.as_view(), name="auth-activation-create-account"),
    path("auth/password-reset", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("me/profile", views.MeProfileView.as_view(), name="me-profile"),
]
