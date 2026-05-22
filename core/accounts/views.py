from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer
from .utils import send_verification_email
from .models import EmailVerification
import requests
import json
from django.conf import settings
from django.shortcuts import redirect
from django.middleware.csrf import get_token


User = get_user_model()

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _cookie_settings(lifetime_seconds, httponly=True):
    """Return a consistent dict of cookie kwargs used site-wide.

    The critical fix: always include path='/' so that cookies set on
    /api/accounts/login/ are sent back for every URL on the site
    (e.g. /downloads/, /api/accounts/auth/status/, etc.).
    Without path='/' the browser scopes the cookie to the request
    path prefix and it never arrives at other endpoints → logout loop.
    """
    return dict(
        max_age=lifetime_seconds,
        httponly=httponly,
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        path='/',          # <-- THE MAIN FIX
    )


def _set_auth_cookies(response, refresh_token_obj):
    """Stamp both JWT cookies onto a response."""
    access_seconds  = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
    refresh_seconds = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())

    response.set_cookie(
        key='access_token',
        value=str(refresh_token_obj.access_token),
        **_cookie_settings(access_seconds),
    )
    response.set_cookie(
        key='refresh_token',
        value=str(refresh_token_obj),
        **_cookie_settings(refresh_seconds),
    )


def _delete_auth_cookies(response):
    """Remove both JWT cookies (path must match what was used when setting)."""
    response.delete_cookie('access_token',  path='/')
    response.delete_cookie('refresh_token', path='/')


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class GetCSRFTokenView(View):
    def get(self, request):
        csrf_token = get_token(request)
        return JsonResponse({"csrfToken": csrf_token})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class EnsureCSRFCookieView(View):
    def get(self, request):
        return JsonResponse({"message": "CSRF cookie set"})


# ---------------------------------------------------------------------------
# REGISTER / VERIFY
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            serializer = RegisterSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse({"errors": serializer.errors}, status=400)
            user = serializer.save()
            verification = EmailVerification.objects.create(user=user)
            send_verification_email(user, verification.token)
            return JsonResponse(
                {"message": "Registration successful. Verify your email."},
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailView(View):
    def get(self, request, token):
        try:
            verification = EmailVerification.objects.get(token=token)
            verification.user.is_verified = True
            verification.user.save()
            verification.delete()
            return redirect("http://127.0.0.1:8000/login/")
        except EmailVerification.DoesNotExist:
            return JsonResponse({"error": "Invalid token"}, status=400)


# ---------------------------------------------------------------------------
# LOGIN / LOGOUT / REFRESH
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            email    = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"error": "Email and password required"}, status=400)

            user = authenticate(email=email, password=password)
            if not user:
                return JsonResponse({"error": "Invalid credentials"}, status=401)
            if not user.is_verified:
                return JsonResponse({"error": "Email not verified"}, status=403)

            refresh  = RefreshToken.for_user(user)
            response = JsonResponse({
                "message": "Login successful",
                "user": {"id": user.id, "email": user.email},
            })
            _set_auth_cookies(response, refresh)
            return response

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RefreshView(View):
    def post(self, request):
        token = request.COOKIES.get('refresh_token')
        if not token:
            try:
                token = json.loads(request.body).get("refresh")
            except Exception:
                token = None

        if not token:
            return JsonResponse({"error": "No refresh token provided"}, status=401)

        try:
            refresh  = RefreshToken(token)
            response = JsonResponse({"message": "Token refreshed"})
            _set_auth_cookies(response, refresh)
            return response
        except Exception:
            return JsonResponse({"error": "Invalid refresh token"}, status=401)


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(View):
    def post(self, request):
        try:
            token = request.COOKIES.get('refresh_token')
            if token:
                RefreshToken(token).blacklist()
        except Exception:
            pass

        response = JsonResponse({"message": "Logged out successfully"})
        _delete_auth_cookies(response)
        return response


# ---------------------------------------------------------------------------
# GOOGLE OAUTH
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(View):
    def get(self, request):
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            "&scope=openid email profile"
            "&access_type=offline"
            "&prompt=consent"
        )
        return redirect(google_auth_url)


@method_decorator(csrf_exempt, name='dispatch')
class GoogleCallbackView(View):
    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return JsonResponse({"error": "No authorization code"}, status=400)

        # Exchange code for Google access token
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code":          code,
                "grant_type":    "authorization_code",
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
            },
            timeout=10,
        )
        token_data   = token_response.json()
        google_token = token_data.get("access_token")
        if not google_token:
            return JsonResponse({"error": "Token exchange failed", "detail": token_data}, status=400)

        # Fetch user info from Google
        user_info_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_token}"},
            timeout=10,
        )
        if user_info_resp.status_code != 200:
            return JsonResponse({"error": "Failed to fetch user info"}, status=400)

        user_info = user_info_resp.json()
        email     = user_info.get("email")
        if not email:
            return JsonResponse({"error": "Email not found in Google response"}, status=400)

        # Get or create local user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_verified": True, "is_active": True},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        elif not user.is_active:
            # Re-activate if somehow deactivated
            user.is_active   = True
            user.is_verified = True
            user.save(update_fields=["is_active", "is_verified"])

        # Issue JWT tokens and redirect with cookies
        refresh  = RefreshToken.for_user(user)
        response = redirect("http://127.0.0.1:8000/downloads/")
        _set_auth_cookies(response, refresh)
        return response


# ---------------------------------------------------------------------------
# AUTH STATUS  (used by every page on load to check if user is logged in)
# ---------------------------------------------------------------------------

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

# csrf_exempt  – GET only; no state change, no CSRF risk.
# ensure_csrf_cookie – plants the csrftoken cookie so the next POST
#   (e.g. download request) from the page has it available.
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(ensure_csrf_cookie, name='dispatch')
class AuthStatusView(View):
    def get(self, request):
        access_token  = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        if not access_token and not refresh_token:
            return JsonResponse(
                {"authenticated": False, "error": "No authentication tokens found"},
                status=401,
            )

        # 1. Try access token first (cheapest — no DB hit)
        if access_token:
            try:
                validated = AccessToken(access_token)
                user      = User.objects.get(id=validated['user_id'])
                return JsonResponse({
                    "authenticated": True,
                    "user": {"id": user.id, "email": user.email, "is_verified": user.is_verified},
                })
            except (InvalidToken, TokenError):
                pass  # Expired — fall through to refresh
            except User.DoesNotExist:
                return JsonResponse(
                    {"authenticated": False, "error": "User not found"},
                    status=401,
                )

        # 2. Try refresh token — issue new pair and update BOTH cookies.
        #    With ROTATE_REFRESH_TOKENS=True the old refresh token is
        #    blacklisted when we call .access_token; we MUST save the new
        #    refresh token cookie or the next reload logs the user out.
        if refresh_token:
            try:
                validated_refresh = RefreshToken(refresh_token)
                user              = User.objects.get(id=validated_refresh['user_id'])

                # Rotate: new access + new refresh
                new_access  = validated_refresh.access_token   # blacklists old refresh
                new_refresh = validated_refresh                 # now holds new refresh token

                response = JsonResponse({
                    "authenticated": True,
                    "token_refreshed": True,
                    "user": {"id": user.id, "email": user.email, "is_verified": user.is_verified},
                })
                _set_auth_cookies(response, new_refresh)
                return response

            except (InvalidToken, TokenError):
                return JsonResponse(
                    {"authenticated": False, "error": "Session expired. Please login again."},
                    status=401,
                )
            except User.DoesNotExist:
                return JsonResponse(
                    {"authenticated": False, "error": "User not found"},
                    status=401,
                )

        return JsonResponse(
            {"authenticated": False, "error": "Invalid authentication tokens"},
            status=401,
        )


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================

from .serializers import ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from .models import PasswordResetToken
from .utils import send_password_reset_email
from django.utils import timezone
from datetime import timedelta


class ChangePasswordView(View):
    def post(self, request):
        access_token = request.COOKIES.get('access_token')
        if not access_token:
            return JsonResponse({"error": "Authentication required"}, status=401)

        try:
            validated_token = AccessToken(access_token)
            user = User.objects.get(id=validated_token['user_id'])
        except Exception:
            return JsonResponse({"error": "Invalid or expired token"}, status=401)

        try:
            data       = json.loads(request.body)
            serializer = ChangePasswordSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse({"errors": serializer.errors}, status=400)

            if not user.check_password(serializer.validated_data['current_password']):
                return JsonResponse({"error": "Current password is incorrect"}, status=400)

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return JsonResponse({"message": "Password changed successfully"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ForgotPasswordView(View):
    def post(self, request):
        try:
            data       = json.loads(request.body)
            serializer = ForgotPasswordSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse({"errors": serializer.errors}, status=400)

            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse(
                    {"message": "If the email exists, a reset link has been sent."},
                    status=200,
                )

            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
            reset_token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            send_password_reset_email(user, reset_token.token)
            return JsonResponse(
                {"message": "If the email exists, a reset link has been sent."},
                status=200,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ResetPasswordView(View):
    def post(self, request, token):
        try:
            data       = json.loads(request.body)
            serializer = ResetPasswordSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse({"errors": serializer.errors}, status=400)

            try:
                reset_token = PasswordResetToken.objects.get(token=token)
            except PasswordResetToken.DoesNotExist:
                return JsonResponse({"error": "Invalid or expired reset link"}, status=400)

            if not reset_token.is_valid():
                return JsonResponse({"error": "Reset link has expired or already been used"}, status=400)

            user = reset_token.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            reset_token.used = True
            reset_token.save()
            return JsonResponse({"message": "Password reset successfully. You can now login."}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
