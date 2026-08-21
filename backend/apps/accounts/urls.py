from django.urls import path

from . import views

urlpatterns = [
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/activate", views.ActivateView.as_view(), name="auth-activate"),
    path("auth/password-reset", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("me/profile", views.MeProfileView.as_view(), name="me-profile"),
]
