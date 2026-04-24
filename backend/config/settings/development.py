from __future__ import annotations

import sys
from pathlib import Path

import environ

from .base import BASE_DIR
from .base import *  # noqa: F401, F403

env = environ.Env(
    DEBUG=(bool, True),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

PHISHING_MODEL_PATH = resolve_backend_path(
    env.path("PHISHING_MODEL_PATH", default=PHISHING_MODEL_PATH)
)
BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS = env.bool(
    "BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS",
    default=True,
)


def _running_pytest() -> bool:
    return "pytest" in sys.modules or any(
        Path(arg).name == "pytest" or arg == "pytest"
        for arg in sys.argv
    )


if _running_pytest():
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }
else:
    DATABASES = {
        "default": env.db("DATABASE_URL"),
    }

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
