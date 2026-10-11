"""FSP ID как OIDC-клиент (Authorization Code Flow).

FSP_MODE=mock — встроенная имитация провайдера: страница выбора участника из data/fsp_registry.json,
code = подписанный JWT с sub = FSP ID. FSP_MODE=oidc — настоящий Keycloak: те же authorize_url / exchange_code,
меняются только переменные окружения FSP_ISSUER, FSP_CLIENT_ID, FSP_CLIENT_SECRET, FSP_REDIRECT_URI.
"""
import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlencode

import jwt

from app import config


@lru_cache
def registry() -> list[dict]:
    path = config.DATA_DIR / "fsp_registry.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _sign(payload: dict, minutes: int = 10) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({**payload, "iat": now, "exp": now + timedelta(minutes=minutes)}, config.JWT_SECRET, algorithm="HS256")


def _read(token: str, purpose: str) -> dict | None:
    try:
        data = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return data if data.get("purpose") == purpose else None


def authorize_url(state: str) -> str:
    """URL страницы входа провайдера (для Keycloak — /protocol/openid-connect/auth)."""
    params = {"client_id": config.FSP_CLIENT_ID, "redirect_uri": config.FSP_REDIRECT_URI, "response_type": "code",
              "scope": "openid profile email fsp_results", "state": state}
    if config.FSP_MODE == "oidc":
        return f"{config.FSP_ISSUER}/protocol/openid-connect/auth?{urlencode(params)}"
    return f"/api/auth/fsp/mock/login?{urlencode(params)}"


def mock_code(fsp_id: str) -> str:
    return _sign({"purpose": "fsp_code", "sub": fsp_id}, minutes=2)


async def exchange_code(code: str) -> dict | None:
    """code → claims (sub, name, email). Для mock — проверка подписи нашего кода."""
    if config.FSP_MODE == "oidc":
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{config.FSP_ISSUER}/protocol/openid-connect/token", data={
                "grant_type": "authorization_code", "code": code, "redirect_uri": config.FSP_REDIRECT_URI,
                "client_id": config.FSP_CLIENT_ID, "client_secret": config.FSP_CLIENT_SECRET})
        if r.status_code != 200:
            return None
        # TODO при подключении реального Keycloak: проверить подпись id_token по JWKS провайдера.
        return jwt.decode(r.json()["id_token"], options={"verify_signature": False})
    data = _read(code, "fsp_code")
    if not data:
        return None
    entry = next((e for e in registry() if e["fsp_id"] == data["sub"]), None)
    if entry is None:
        return None
    return {"sub": entry["fsp_id"], "name": entry.get("full_name"), "email": entry.get("email"), "iss": config.FSP_ISSUER}
