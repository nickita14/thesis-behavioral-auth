from __future__ import annotations

import logging

from django.http import Http404
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import BehaviorSession

logger = logging.getLogger(__name__)


class IsSessionOwner(BasePermission):
    """Allow access only if request.user owns the BehaviorSession
    identified by the URL kwarg 'token'.

    The resolved session is cached on request.behavior_session so that
    views can use it without issuing a second database query.
    Returns False (→ 404 in views) rather than raising PermissionDenied
    so that foreign session tokens are indistinguishable from missing ones.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        token = view.kwargs.get("token")
        if not token:
            return False

        try:
            session = BehaviorSession.objects.select_related("user").get(
                session_token=token
            )
        except BehaviorSession.DoesNotExist:
            logger.warning(
                "IsSessionOwner: session_token=%s not found (user=%s)",
                token,
                getattr(request.user, "username", "anonymous"),
            )
            raise Http404

        if session.user_id != request.user.pk:
            logger.warning(
                "IsSessionOwner: user=%s attempted access to session owned by user=%s",
                request.user.pk,
                session.user_id,
            )
            raise Http404

        request.behavior_session = session  # type: ignore[attr-defined]
        return True
