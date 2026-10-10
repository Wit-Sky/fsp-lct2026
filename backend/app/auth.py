"""Пароли (bcrypt), JWT (24 часа), зависимости FastAPI для проверки роли."""
import secrets
from datetime import datetime, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db import get_session
from app.errors import ApiError
from app.models import Employer, User
from sqlalchemy import select

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def hash_password(p: str) -> str:
    return _pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return _pwd.verify(p, h)
    except ValueError:
        return False


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def make_token(user: User, ttl=None, **extra) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + (ttl or config.JWT_TTL), **extra}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise ApiError(401, "invalid_token", "Токен недействителен или истёк")


async def current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                       session: AsyncSession = Depends(get_session)) -> User:
    if cred is None:
        raise ApiError(401, "unauthorized", "Требуется авторизация")
    data = decode_token(cred.credentials)
    if data.get("purpose"):
        raise ApiError(401, "invalid_token", "Токен не для доступа к API")
    user = await session.get(User, int(data["sub"]))
    if user is None:
        raise ApiError(401, "invalid_token", "Пользователь не найден")
    return user


async def candidate(user: User = Depends(current_user)) -> User:
    if user.role != "candidate":
        raise ApiError(403, "forbidden", "Доступно только кандидату")
    return user


async def employer_user(user: User = Depends(current_user)) -> User:
    if user.role != "employer":
        raise ApiError(403, "forbidden", "Доступно только работодателю")
    return user


async def employer(user: User = Depends(employer_user), session: AsyncSession = Depends(get_session)) -> Employer:
    """Компания текущего работодателя (создаётся пустой при первом обращении)."""
    emp = (await session.execute(select(Employer).where(Employer.owner_id == user.id))).scalar_one_or_none()
    if emp is None:
        emp = Employer(owner_id=user.id, name="Новая компания")
        session.add(emp)
        await session.commit()
        await session.refresh(emp)
    return emp
