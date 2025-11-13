from django.conf import settings
from django.contrib.auth.password_validation import validate_password

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .utils import get_user
from .serializers import (
    RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer,
    OTPLoginSerializer, VerifyOTPSerializer,
    ForgotPasswordRequestSerializer, ForgotPasswordVerifySerializer, ForgotPasswordResetSerializer
)
from services.token_service import is_refresh_token_valid, store_refresh_token, delete_refresh_token
from services.otp_service import (
    generate_otp, store_otp, verify_otp, increment_attempts,
    create_reset_token, get_userid_for_reset_token, delete_reset_token
)
from services.notification_services import send_email_otp, send_sms_otp


# -------------------------------
# Registration and Authentication
# -------------------------------

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        store_refresh_token(user.id, str(refresh))

        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.get('refresh')
            if refresh_token:
                try:
                    token_obj = RefreshToken(refresh_token)
                    uid = token_obj.get('user_id') or token_obj.get('user')
                    if uid:
                        store_refresh_token(uid, refresh_token)
                except TokenError:
                    pass
        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        old_refresh = request.data.get("refresh")
        if not old_refresh:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        if not is_refresh_token_valid(old_refresh):
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)

        new_refresh = response.data.get("refresh")
        if new_refresh:
            try:
                token_obj = RefreshToken(new_refresh)
                uid = token_obj.get('user_id') or token_obj.get('user')
                if uid:
                    store_refresh_token(uid, new_refresh)
                    delete_refresh_token(old_refresh)
            except TokenError:
                pass
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_obj = RefreshToken(refresh_token)
            uid = token_obj.get('user_id') or token_obj.get('user')
            # Compare UUIDs directly (both are UUID strings or objects)
            if uid and str(uid) != str(request.user.id):
                return Response({"detail": "Token does not belong to authenticated user"}, status=status.HTTP_403_FORBIDDEN)
        except TokenError:
            pass

        delete_refresh_token(refresh_token)
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)


# -------------------------------
# OTP: Email and Phone Verification
# -------------------------------

class GetEmailOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(email, kind="email")
        if not user:
            return Response({"detail": "If the email exists, OTP has been sent."}, status=status.HTTP_200_OK)

        otp = generate_otp()
        store_otp("email", email, otp)
        send_email_otp(email, otp)
        return Response({"detail": "OTP sent to email"}, status=status.HTTP_200_OK)


class VerifyEmailOTPView(APIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        otp = serializer.validated_data["otp"]

        attempts = increment_attempts("email", identifier, window_seconds=300)
        if attempts > 5:
            return Response({"detail": "Too many attempts. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        ok = verify_otp("email", identifier, otp)
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(identifier, kind="email")
        if not user:
            return Response({"detail": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified successfully"}, status=status.HTTP_200_OK)


class GetPhoneOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return Response({"detail": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(phone_number, kind="phone")
        if not user:
            return Response({"detail": "If the number exists, OTP has been sent."}, status=status.HTTP_200_OK)

        otp = generate_otp()
        store_otp("phone", phone_number, otp)
        send_sms_otp(phone_number, otp)
        return Response({"detail": "OTP sent to phone"}, status=status.HTTP_200_OK)


class VerifyPhoneOTPView(APIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        otp = serializer.validated_data["otp"]

        attempts = increment_attempts("phone", identifier, window_seconds=300)
        if attempts > 5:
            return Response({"detail": "Too many attempts. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        ok = verify_otp("phone", identifier, otp)
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(identifier, kind="phone")
        if not user:
            return Response({"detail": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
        return Response({"detail": "Phone verified successfully"}, status=status.HTTP_200_OK)


# -------------------------------
# OTP Login
# -------------------------------

class GetLoginOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        kind = request.data.get("kind")
        identifier = request.data.get("identifier")

        if not kind or not identifier:
            return Response({"detail": "Kind and identifier are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(identifier, kind)
        if not user:
            return Response({"detail": "If the account exists, OTP has been sent."}, status=status.HTTP_200_OK)

        otp = generate_otp()
        store_otp(f"login:{kind}", identifier, otp)

        if kind == "email":
            send_email_otp(identifier, otp)
        elif kind == "phone":
            send_sms_otp(identifier, otp)
        else:
            return Response({"detail": "Invalid kind"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "OTP sent successfully"}, status=status.HTTP_200_OK)


class OTPLoginView(APIView):
    serializer_class = OTPLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["kind"]
        identifier = serializer.validated_data["identifier"]
        otp = serializer.validated_data["otp"]

        attempts = increment_attempts(kind, identifier, window_seconds=300)
        if attempts > 5:
            return Response({"detail": "Too many attempts. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        ok = verify_otp(f"login:{kind}", identifier, otp)
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user(identifier, kind)
        if not user:
            return Response({"detail": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        store_refresh_token(user.id, str(refresh))

        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


# -------------------------------
# Forgot Password (OTP-based)
# -------------------------------

class ForgotPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["kind"]
        identifier = serializer.validated_data["identifier"].strip()

        attempts = increment_attempts(f"password_request:{kind}", identifier, window_seconds=60)
        if attempts > 5:
            return Response({"detail": "Too many OTP requests. Try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            if kind == "email":
                user = User.objects.get(email=identifier, is_email_verified=True)
            else:
                user = User.objects.get(phone_no=identifier, is_phone_verified=True)
        except User.DoesNotExist:
            return Response({"detail": "If that account exists, an OTP has been sent."}, status=status.HTTP_200_OK)

        otp = generate_otp()
        store_otp(f"password:{kind}", identifier, otp)
        if kind == "email":
            send_email_otp(identifier, otp)
        else:
            send_sms_otp(identifier, otp)

        return Response({"detail": "If that account exists, an OTP has been sent."}, status=status.HTTP_200_OK)


class ForgotPasswordVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["kind"]
        identifier = serializer.validated_data["identifier"].strip()
        otp = serializer.validated_data["otp"].strip()

        attempts = increment_attempts(f"password_verify:{kind}", identifier, window_seconds=300)
        if attempts > 5:
            return Response({"detail": "Too many attempts. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        ok = verify_otp(f"password:{kind}", identifier, otp)
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if kind == "email":
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone_no=identifier)
        except User.DoesNotExist:
            return Response({"detail": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        reset_token = create_reset_token(user.id)
        return Response({"reset_token": reset_token, "detail": "OTP verified. Use reset_token to set new password."}, status=status.HTTP_200_OK)


class ForgotPasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.validated_data["reset_token"]
        new_password = serializer.validated_data["new_password"]

        user_id = get_userid_for_reset_token(reset_token)
        if not user_id:
            return Response({"detail": "Invalid or expired reset token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        delete_reset_token(reset_token)

        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)
