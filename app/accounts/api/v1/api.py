from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from app.accounts.models import User
from core.utils import get_user

from app.accounts.api.v1.serializers import (
    RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer, GetOTPSerializer, 
    VerifyOTPSerializer, ForgotPasswordRequestSerializer, ForgotPasswordVerifySerializer, 
    ForgotPasswordResetSerializer,
)

from services.token_service import (
    is_refresh_token_valid, store_refresh_token, delete_refresh_token,
)

from app.accounts.services.auth_service import login_user, logout_user
from app.accounts.services.otp_flow_service import send_otp, verify_otp_flow
from app.accounts.services.password_reset_service import (
    request_password_reset, verify_password_reset_otp, reset_password,
)

# -------------------------------
# Registration and Authentication
# -------------------------------

class RegisterAPI(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = login_user(user)
        return Response({
            "message": "User created successfully",
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),},
            status=status.HTTP_201_CREATED,
        )

class LoginAPI(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request):
        response = super().post(request)
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
                
    


class RefreshAPI(TokenRefreshView):
    def post(self, request):
        old_refresh = request.data.get("refresh")
        if not old_refresh:
            return Response({"message": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        if not is_refresh_token_valid(old_refresh):
            return Response({"message": "Invalid refresh token"}, status=401)

        response = super().post(request)
        new_refresh = response.data.get("refresh")

        if new_refresh:
            token = RefreshToken(new_refresh)
            store_refresh_token(token["user_id"], new_refresh)
            delete_refresh_token(old_refresh)

        return response


class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout_user(
            refresh_token=request.data.get("refresh"),
            request_user=request.user,
        )
        return Response({"message": "Logged out"}, status=205)

class GetUserAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "Success", "data": UserSerializer(request.user).data}, status=status.HTTP_200_OK)
    
# ---------------------------------------
# OTP: Email / Phone Verification & Login
# ---------------------------------------

class GetOTPAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GetOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        send_otp(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            purpose=serializer.validated_data["purpose"],
        )
        return Response({"message": "OTP sent"})

class VerifyOTPAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_otp_flow(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            otp=serializer.validated_data["otp"],
            purpose="verify",
        )

        user = get_user(serializer.validated_data["identifier"], serializer.validated_data["kind"])
        if not user:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.validated_data["kind"] == "email":
            user.is_email_verified = True
        else:
            user.is_phone_verified = True
        user.save()
        
        return Response({"message": "Verified"}, status=status.HTTP_200_OK)

class OTPLoginAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_otp_flow(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            otp=serializer.validated_data["otp"],
            purpose="login",
        )

        user = get_user(
            serializer.validated_data["identifier"],
            serializer.validated_data["kind"],
        )

        refresh = login_user(user)
        return Response({
            "message": "User logged in successfully",
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),}, 
            status=status.HTTP_200_OK
        )

# -------------------------------
# Forgot Password (OTP-based)
# -------------------------------

class ForgotPasswordRequestAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
        )
        return Response({"message": "OTP sent"})

class ForgotPasswordVerifyAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_token = verify_password_reset_otp(**serializer.validated_data)
        return Response({"message": reset_token})

class ForgotPasswordResetAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def put(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_password(**serializer.validated_data)
        return Response({"message": "Password updated"})
