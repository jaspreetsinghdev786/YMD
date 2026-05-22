from django.urls import path
from .views import (
    RegisterView, VerifyEmailView, GoogleLoginView, GoogleCallbackView, 
    LogoutView, LoginView, RefreshView, AuthStatusView, GetCSRFTokenView,
    ChangePasswordView, ForgotPasswordView, ResetPasswordView
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("verify/<uuid:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("google/login/", GoogleLoginView.as_view()),
    path("google/callback/", GoogleCallbackView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("login/", LoginView.as_view()),
    path("refresh/", RefreshView.as_view()),
    path('auth/status/', AuthStatusView.as_view(), name='auth_status'),
    path('csrf-token/', GetCSRFTokenView.as_view(), name='csrf-token'),
    
    # Password management
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uuid:token>/', ResetPasswordView.as_view(), name='reset-password'),
]
