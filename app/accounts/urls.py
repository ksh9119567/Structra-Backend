from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView, LoginView, LogoutView, GetLoginOTPView, GetEmailOTPView, GetPhoneOTPView,
    OTPLoginView, VerifyEmailOTPView, VerifyPhoneOTPView, ForgotPasswordRequestView, 
    ForgotPasswordVerifyView, ForgotPasswordResetView
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("get-user/", RegisterView.as_view(), name="get_user"),
    path('login/', LoginView.as_view(), name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('otp/login/', GetLoginOTPView.as_view(), name='get_login_otp'),
    path('otp/email/', GetEmailOTPView.as_view(), name='get_email_otp'),
    path('otp/phone/', GetPhoneOTPView.as_view(), name='get_phone_otp'),
    path('otp/verify/login/', OTPLoginView.as_view(), name='verify_login_otp'),
    path('otp/verify/email/', VerifyEmailOTPView.as_view(), name='verify_email_otp'),
    path('otp/verify/phone/', VerifyPhoneOTPView.as_view(), name='verify_phone_otp'),
    path('forgot-password/request/', ForgotPasswordRequestView.as_view(), name='forgot_password_request'),
    path('forgot-password/verify/', ForgotPasswordVerifyView.as_view(), name='forgot_password_verify'),
    path('forgot-password/reset/', ForgotPasswordResetView.as_view(), name='forgot_password_reset'),
]
