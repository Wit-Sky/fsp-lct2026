"""Код перехода — 60 секунд и одно использование; OIDC state — 10 минут и одно использование.

Оба связаны с пользователем и HttpOnly cookie браузера. Атомарные UPDATE/DELETE работают
между процессами API и переживают перезапуск; bearer-токен остаётся в заголовке POST /start.
"""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import utcnow
from app.errors import ApiError
from app.models import FspAuthorization

CODE_TTL = 60
STATE_TTL = 600
COOKIE_NAME = "fsp_link"
COOKIE_PATH = "/api/auth/fsp"
PRIVATE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def start(session: AsyncSession, user_id: int) -> tuple[str, str]:
    now = utcnow()
    await session.execute(delete(FspAuthorization).where(and_(
        FspAuthorization.expires_at <= now,
        or_(FspAuthorization.state_expires_at.is_(None), FspAuthorization.state_expires_at <= now))))
    code, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session.add(FspAuthorization(code_hash=digest(code), browser_hash=digest(binding), user_id=user_id,
                                 expires_at=now + timedelta(seconds=CODE_TTL)))
    await session.commit()
    return code, binding


async def authorize(session: AsyncSession, code: str, binding: str | None) -> str:
    if not binding:
        raise ApiError(400, "invalid_code", "Сессия связывания истекла, начните заново")
    state = secrets.token_urlsafe(32)
    now = utcnow()
    uid = (await session.execute(update(FspAuthorization).where(
        FspAuthorization.code_hash == digest(code), FspAuthorization.browser_hash == digest(binding),
        FspAuthorization.expires_at > now, FspAuthorization.state_hash.is_(None)
    ).values(state_hash=digest(state), state_expires_at=now + timedelta(seconds=STATE_TTL))
       .returning(FspAuthorization.user_id))).scalar_one_or_none()
    if uid is None:
        raise ApiError(400, "invalid_code", "Код истёк или уже использован, начните связывание заново")
    await session.commit()
    return state


def _state_conditions(state: str, binding: str):
    return (FspAuthorization.state_hash == digest(state),
            FspAuthorization.browser_hash == digest(binding), FspAuthorization.state_expires_at > utcnow())


async def user_for_state(session: AsyncSession, state: str, binding: str | None, consume: bool = False) -> int:
    if not binding:
        raise ApiError(400, "invalid_state", "Сессия связывания истекла, начните заново")
    if consume:
        stmt = delete(FspAuthorization).where(*_state_conditions(state, binding)).returning(FspAuthorization.user_id)
    else:
        stmt = select(FspAuthorization.user_id).where(*_state_conditions(state, binding))
    uid = (await session.execute(stmt)).scalar_one_or_none()
    if uid is None:
        raise ApiError(400, "invalid_state", "Сессия связывания истекла или уже использована, начните заново")
    if consume:
        await session.commit()
    return uid
