from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model — extend here as behavioral profile fields are added."""

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
