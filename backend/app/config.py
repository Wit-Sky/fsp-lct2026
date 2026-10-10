"""Настройки из переменных окружения (полный список — docs/backend.md и backend/.env.example)."""
import os
from datetime import timedelta
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


BASE_DIR = Path(__file__).resolve().parent            # backend/app
# Локально: <repo>/data; в контейнере (/app/app/config.py) — /data (монтируется томом).
DATA_DIR = Path(_env("DATA_DIR", str(BASE_DIR.parents[1] / "data")))

DATABASE_URL = _env("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
JWT_SECRET = _env("JWT_SECRET", "dev-only-secret-change-me-in-production-32b")
JWT_TTL = timedelta(hours=int(_env("JWT_TTL_HOURS", "24")))
CORS_ORIGINS = [o.strip() for o in _env("CORS_ORIGINS", "http://localhost:5173,http://localhost").split(",") if o.strip()]
FRONTEND_URL = _env("FRONTEND_URL", "http://localhost:5173")

# Кулдаун смены грейда: 30 дней; на демо — DEMO_COOLDOWN_MIN минут (0 — выключить демо-режим).
COOLDOWN_DAYS = int(_env("COOLDOWN_DAYS", "30"))
DEMO_COOLDOWN_MIN = int(_env("DEMO_COOLDOWN_MIN", "2"))


def cooldown() -> timedelta:
    if DEMO_COOLDOWN_MIN > 0:
        return timedelta(minutes=DEMO_COOLDOWN_MIN)
    return timedelta(days=COOLDOWN_DAYS)


TEST_TIME_LIMIT = timedelta(minutes=int(_env("TEST_TIME_LIMIT_MIN", "5")))
ITEM_TIME_LIMIT = timedelta(seconds=int(_env("ITEM_TIME_LIMIT_SEC", "90")))

# Регистрация: код подтверждения возвращается в ответе (имитация письма) при DEMO_MODE=1.
DEMO_MODE = _env("DEMO_MODE", "1") == "1"
SEED_ON_START = _env("SEED_ON_START", "1") == "1"

# Имитация FSP ID, устроенная как OIDC-клиент: для настоящего Keycloak меняются только эти значения.
FSP_MODE = _env("FSP_MODE", "mock")                   # mock | oidc
FSP_ISSUER = _env("FSP_ISSUER", "http://localhost:8000/api/auth/fsp/mock")
FSP_CLIENT_ID = _env("FSP_CLIENT_ID", "fsp-talent")
FSP_CLIENT_SECRET = _env("FSP_CLIENT_SECRET", "")
FSP_REDIRECT_URI = _env("FSP_REDIRECT_URI", "http://localhost:8000/api/auth/fsp/callback")
