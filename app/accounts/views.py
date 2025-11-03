from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer
from rest_framework import status
from services.token_service import is_refresh_token_valid, store_refresh_token, delete_refresh_token

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
            user = self.get_user(request.data.get('email'))
            
            if user and refresh_token:
                store_refresh_token(user.id, refresh_token)

        return response

    def get_user(self, email):
        """Utility to fetch user by email"""
        from .models import User
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not is_refresh_token_valid(refresh_token):
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)

        new_refresh_token = response.data.get("refresh")
        if new_refresh_token:
            store_refresh_token(request.user.id, new_refresh_token)

        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        delete_refresh_token(refresh_token)
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)
    
