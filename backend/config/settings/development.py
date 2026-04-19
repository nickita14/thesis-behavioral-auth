from __future__ import annotations

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

DATABASES = {
    "default": env.db("DATABASE_URL"),
}
