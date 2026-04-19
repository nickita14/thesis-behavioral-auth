from __future__ import annotations

import logging

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    """GET /api/auth/csrf/

    Sets the csrftoken cookie so the SPA can read it on startup and
    attach it to subsequent state-changing requests as X-CSRFToken.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request) -> Response:
        return Response({"detail": "CSRF cookie set"})


class RegisterView(APIView):
    """POST /api/auth/register/

    Creates a new user account. The user is immediately active.
    Email verification is intentionally omitted in v1.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/auth/login/

    Authenticates with username + password and creates a Django session.
    Returns a generic error on failure — does not reveal whether the
    username or the password was wrong (information leakage prevention).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            logger.warning(
                "LoginView: failed attempt for username=%r from ip=%s",
                serializer.validated_data["username"],
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    """POST /api/auth/logout/

    Terminates the current session. Requires authentication so that
    anonymous clients cannot generate spurious session flushes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/

    Returns the authenticated user's profile. Used by the SPA on startup
    to restore session state without a separate login roundtrip.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)
