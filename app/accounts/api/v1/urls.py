from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from app.accounts.api.v1.api import (
    RegisterAPI, LoginAPI, LogoutAPI, RefreshAPI, GetUserAPI, GetOTPAPI, VerifyOTPAPI, OTPLoginAPI, 
    ForgotPasswordRequestAPI, ForgotPasswordVerifyAPI, ForgotPasswordResetAPI
)


urlpatterns = [
    # Authentication
    path("register/", RegisterAPI.as_view(), name="register"),
    path('login/', LoginAPI.as_view(), name='login'),
    path("logout/", LogoutAPI.as_view(), name="logout"),
    path('token/refresh/', RefreshAPI.as_view(), name='token_refresh'),
    
    # User
    path("get-user/", GetUserAPI.as_view(), name="get_user"),
    path("update_user/", GetUserAPI.as_view(), name="update_user"),
    path("delete_user/", GetUserAPI.as_view(), name="delete_user"),
    
    # Verification
    path('get-otp/', GetOTPAPI.as_view(), name='get_login_otp'),
    path('verify-otp/', VerifyOTPAPI.as_view(), name="verify_otp"),
    path('verify-otp/login/', OTPLoginAPI.as_view(), name='verify_login_otp'),
    
    # Password Reset
    path('forgot-password/request/', ForgotPasswordRequestAPI.as_view(), name='forgot_password_request'),
    path('forgot-password/verify/', ForgotPasswordVerifyAPI.as_view(), name='forgot_password_verify'),
    path('forgot-password/reset/', ForgotPasswordResetAPI.as_view(), name='forgot_password_reset'),
]
