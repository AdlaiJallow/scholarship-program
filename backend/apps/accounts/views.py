from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import log_action

from . import services
from .models import User
from .serializers import (
    CreateAccountSerializer,
    LoginSerializer,
    OfficerProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendCodeSerializer,
    StudentProfileSerializer,
    VerifyCodeSerializer,
    VerifyIdentitySerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        ip_address = getattr(request, "audit_ip", None)

        if services.is_locked_out(email, ip_address):
            return Response(
                {"detail": "Too many failed attempts. Please try again later or reset your password."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(request, username=email, password=password)
        if user is None:
            services.record_failed_login(email, ip_address, request=request)
            return Response({"detail": "Incorrect email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        services.record_successful_login(user, request=request)
        return Response({"user_type": user.user_type, "email": user.email, "must_change_password": user.must_change_password})


class LogoutView(APIView):
    def post(self, request):
        log_action(AuditLog.Action.LOGOUT, actor=request.user, request=request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyIdentityView(APIView):
    """
    Step 1-3 of self-activation: match a MAT number + UTG email against the
    Ministry's imported records and email a one-time code. None of these
    activation endpoints ever authenticate a session, so DRF never enforces
    CSRF on them (SessionAuthentication only checks CSRF once
    request.user is already authenticated) — the session stays anonymous
    for the whole multi-step flow until CreateAccountView's login() call.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "activation-verify-identity"

    def post(self, request):
        serializer = VerifyIdentitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.verify_identity(request=request, **serializer.validated_data)
        except services.AlreadyActivatedError as exc:
            return Response({"detail": str(exc), "already_activated": True}, status=status.HTTP_409_CONFLICT)
        except services.IdentityMismatchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "We've sent a verification code to your UTG email."}, status=status.HTTP_200_OK)


class VerifyCodeView(APIView):
    """Step 4-5: validate the emailed code and issue a short-lived token for account creation."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "activation-verify-code"

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = services.verify_code(request=request, **serializer.validated_data)
        except services.AlreadyActivatedError as exc:
            return Response({"detail": str(exc), "already_activated": True}, status=status.HTTP_409_CONFLICT)
        except services.IdentityMismatchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except services.CodeLockedOutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except services.CodeVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"verification_token": token, "detail": "Identity verified."}, status=status.HTTP_200_OK)


class ResendCodeView(APIView):
    """Section 9: resend the verification code, invalidating the previous one."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "activation-resend-code"

    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.resend_verification_code(request=request, **serializer.validated_data)
        except services.AlreadyActivatedError as exc:
            return Response({"detail": str(exc), "already_activated": True}, status=status.HTTP_409_CONFLICT)
        except services.IdentityMismatchError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except services.ResendCooldownError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "retry_after_seconds": exc.retry_after_seconds,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except services.ResendLimitExceededError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response(
            {"detail": "A new verification code has been sent to your UTG email. Your previous code is no longer valid."},
            status=status.HTTP_202_ACCEPTED,
        )


class CreateAccountView(APIView):
    """Step 6: create the User/Student once identity + code are verified."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "activation-create-account"

    def post(self, request):
        serializer = CreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.create_student_account(request=request, **serializer.validated_data)
        except services.AlreadyActivatedError as exc:
            return Response({"detail": str(exc), "already_activated": True}, status=status.HTTP_409_CONFLICT)
        except services.VerificationTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({"user_type": user.user_type, "email": user.email}, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-password-reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        # Always return 202 regardless of whether the account exists, so this
        # endpoint cannot be used to enumerate registered email addresses.
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.PORTAL_BASE_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Reset your Scholarship Portal password",
                f"Use this link to reset your password: {reset_link}\nIf you did not request this, ignore this email.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            log_action(AuditLog.Action.PASSWORD_RESET_REQUESTED, actor=user, request=request)
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        log_action(AuditLog.Action.PASSWORD_RESET_COMPLETED, actor=user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type == User.UserType.STUDENT:
            data = StudentProfileSerializer(user.student_profile).data
        else:
            data = OfficerProfileSerializer(user.officer_profile).data
        data["user_type"] = user.user_type
        return Response(data)
