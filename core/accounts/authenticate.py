# accounts/authenticate.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # First check for token in header (fallback)
        header = self.get_header(request)

        if header is None:
            # Try to get token from cookie
            raw_token = request.COOKIES.get('access_token')
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        # IMPORTANT: Only enforce CSRF for cookie-based authentication
        # Check if token came from cookie (not header)
        if header is None:
            self.enforce_csrf(request)

        return self.get_user(validated_token), validated_token

    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for cookie-based authentication.

        Safe methods (GET, HEAD, OPTIONS) are exempt — Django's own
        CsrfViewMiddleware works the same way. This allows the auth-status
        check (a GET request) to succeed right after a Google OAuth redirect,
        when the browser does not yet have a csrftoken cookie.
        """
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return  # Read-only; no state change, no CSRF risk

        def dummy_get_response(request):  # pragma: no cover
            return None

        check = CSRFCheck(dummy_get_response)
        # Populates request.META['CSRF_COOKIE']
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)
