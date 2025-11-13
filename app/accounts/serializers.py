from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth.password_validation import validate_password

from .models import User


class UserSerializer(serializers.ModelSerializer):
    # expose id directly (it's now the actual field name)
    phone_number = serializers.CharField(source="phone_no", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "profile_picture", "phone_number"]
        read_only_fields = ["id"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    # accept phone_number in API but map to model's phone_no
    phone_number = serializers.CharField(required=False, allow_blank=True, write_only=True, source="phone_no")

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password", "phone_number"]

    def create(self, validated_data):
        # serializer `source` mapping puts phone_no into validated_data when provided
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        # note: user.is_email_verified remains False until OTP verified
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['username'] = user.username
        return token


class OTPLoginSerializer(serializers.Serializer):
    kind = serializers.CharField()
    identifier = serializers.CharField()
    otp = serializers.CharField()
    
class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # email or phone
    otp = serializers.CharField()

# accounts/serializers.py (append)

class ForgotPasswordRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()

class ForgotPasswordVerifySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()
    otp = serializers.CharField()

class ForgotPasswordResetSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        validate_password(value)
        return value
