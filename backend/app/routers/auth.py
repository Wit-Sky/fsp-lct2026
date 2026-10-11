import html
import logging

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config, fsp_oidc
from app import auth as security
from app.db import get_session, utcnow
from app.errors import ApiError, responses
from app.models import CandidateProfile, ExternalIdentity, User, VerifiedResult
from app.schemas import FspStartOut, LoginIn, RegisterIn, RegisterOut, TokenOut, VerifyIn
from app.services import demo as demo_svc, fsp_link
from app.services import profile as profile_svc

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("auth")

DEMO_EMAILS = {"candidate": "candidate@demo.fsp", "employer": "employer@demo.fsp"}


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=security.make_token(user), role=user.role, user_id=user.id)


@router.post("/register", response_model=RegisterOut, status_code=201, summary="Регистрация по email",
             description="Создаёт пользователя и отправляет 6-значный код подтверждения. В демо-режиме код возвращается "
                         "в ответе и пишется в лог (имитация письма).", responses=responses(409, 422))
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    email = body.email.lower()
    if (await session.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise ApiError(409, "email_taken", "Пользователь с таким email уже зарегистрирован")
    code = security.new_code()
    user = User(email=email, password_hash=security.hash_password(body.password), role=body.role, verify_code=code)
    session.add(user)
    await session.flush()
    if body.role == "candidate":
        session.add(CandidateProfile(user_id=user.id, full_name="", skills=[], visible_fields={}))
    await session.commit()
    log.warning("Код подтверждения для %s: %s", email, code)
    return RegisterOut(user_id=user.id, email=email, verify_code=code if config.DEMO_MODE else None,
                       message="Код подтверждения отправлен на почту")


@router.post("/verify", response_model=TokenOut, summary="Подтверждение email кодом",
             description="Проверяет код из письма, помечает email подтверждённым и сразу выдаёт токен.",
             responses=responses(400, 404))
async def verify(body: VerifyIn, session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user is None:
        raise ApiError(404, "not_found", "Пользователь не найден")
    if not user.email_verified:
        if user.verify_code != body.code:
            raise ApiError(400, "invalid_code", "Неверный код подтверждения")
        user.email_verified, user.verify_code = True, None
        await session.commit()
    return _token(user)


@router.post("/login", response_model=TokenOut, summary="Вход по email и паролю",
             description="JWT на 24 часа. Email должен быть подтверждён.", responses=responses(401, 403))
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise ApiError(401, "invalid_credentials", "Неверный email или пароль")
    if not user.email_verified:
        raise ApiError(403, "email_not_verified", "Подтвердите email кодом из письма")
    return _token(user)


@router.post("/demo/{role}", response_model=TokenOut, summary="Вход демо-аккаунтом (для жюри)",
             description="Мгновенный вход: candidate@demo.fsp или employer@demo.fsp. Каждый вход кандидата сбрасывает "
                         "его тесты, категорию, приглашения и связь ФСП, чтобы жюри прошло путь с нуля.",
             responses=responses(404))
async def demo_login(role: str, session: AsyncSession = Depends(get_session)):
    if not config.DEMO_MODE:
        raise ApiError(404, "not_found", "Демо-вход отключён")
    email = DEMO_EMAILS.get(role)
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none() if email else None
    if user is None or not user.is_demo:
        raise ApiError(404, "not_found", "Демо-аккаунт не найден (сид не загружен?)")
    if role == "candidate":
        await demo_svc.reset_candidate(session, user)
        await session.commit()
    return _token(user)


# ---------------------------------------------------------------- FSP ID (OIDC, имитация)

def _set_link_cookie(response: Response, binding: str):
    response.set_cookie(fsp_link.COOKIE_NAME, binding, httponly=True, samesite="lax",
                        secure=config.FRONTEND_URL.startswith("https://"),
                        max_age=fsp_link.STATE_TTL, path=fsp_link.COOKIE_PATH)


@router.post("/fsp/start", response_model=FspStartOut, summary="Подготовить связывание FSP ID",
             description="Authorization: Bearer JWT. Возвращает URL с одноразовым кодом на 60 секунд, "
                         "привязанным к кандидату и HttpOnly cookie браузера. JWT в URL не передаётся.",
             responses=responses(401, 403))
async def fsp_start(response: Response, user: User = Depends(security.candidate),
                    session: AsyncSession = Depends(get_session)):
    code, binding = await fsp_link.start(session, user.id)
    _set_link_cookie(response, binding)
    response.headers.update(fsp_link.PRIVATE_HEADERS)
    return FspStartOut(authorize_url=f"/api/auth/fsp/authorize?code={code}", expires_in=fsp_link.CODE_TTL)


@router.get("/fsp/authorize", summary="Связать профиль с FSP ID (начало OIDC)",
            description="Браузерный переход по authorize_url из POST /auth/fsp/start. Код используется один раз, "
                        "затем переход на страницу FSP ID; параметр token больше не принимается.",
            response_class=RedirectResponse, status_code=302, responses=responses(400))
async def fsp_authorize(code: str = Query(..., min_length=32, max_length=128),
                        binding: str | None = Cookie(None, alias=fsp_link.COOKIE_NAME),
                        session: AsyncSession = Depends(get_session)):
    state = await fsp_link.authorize(session, code, binding)
    response = RedirectResponse(fsp_oidc.authorize_url(state), status_code=302, headers=fsp_link.PRIVATE_HEADERS)
    _set_link_cookie(response, binding)
    return response


@router.get("/fsp/mock/login", response_class=HTMLResponse, include_in_schema=False)
async def fsp_mock_login(state: str, redirect_uri: str = config.FSP_REDIRECT_URI, q: str = "",
                         binding: str | None = Cookie(None, alias=fsp_link.COOKIE_NAME),
                         session: AsyncSession = Depends(get_session)):
    """Страница «ФСП ID (демо)»: выбор участника из реестра. Уже связанные записи недоступны."""
    if config.FSP_MODE != "mock":
        raise ApiError(404, "not_found", "Имитация FSP ID отключена")
    await fsp_link.user_for_state(session, state, binding)
    linked = set((await session.execute(select(ExternalIdentity.subject).where(ExternalIdentity.provider == "fsp"))).scalars())
    rows = []
    for e in fsp_oidc.registry():
        n = len(e.get("results", []))
        busy = e["fsp_id"] in linked
        link = f"/api/auth/fsp/callback?code={fsp_oidc.mock_code(e['fsp_id'])}&state={html.escape(state)}"
        rows.append((busy, f"<li class='{'busy' if busy else ''}' data-q='{html.escape((e['full_name'] + ' ' + e['fsp_id']).lower())}'>"
                           + (f"<span>{html.escape(e['full_name'])}</span>" if busy else f"<a href='{link}'>{html.escape(e['full_name'])}</a>")
                           + f" <small>{e['fsp_id']} · результатов: {n}{' · уже связан' if busy else ''}</small></li>"))
    rows.sort(key=lambda r: r[0])
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ФСП ID (демо)</title><style>
body{{font-family:Montserrat,Arial,sans-serif;background:#310F53;color:#1C1D22;margin:0;padding:24px}}
.card{{max-width:640px;margin:0 auto;background:#fff;border-radius:16px;padding:24px}}
h1{{color:#520978;margin-top:0}} input{{width:100%;padding:10px;border:2px solid #8A83D1;border-radius:8px;font-size:16px;box-sizing:border-box}}
ul{{list-style:none;padding:0;max-height:60vh;overflow:auto}} li{{padding:8px 4px;border-bottom:1px solid #FFD6E4}}
a{{color:#FF0053;font-weight:600;text-decoration:none}} small{{color:#666}} .busy span{{color:#999}}
.note{{background:#FFD6E4;padding:8px 12px;border-radius:8px;font-size:14px}}</style></head><body><div class="card">
<h1>ФСП ID <small>(демо)</small></h1>
<p class="note">Имитация провайдера OIDC на базе Keycloak. Выберите участника реестра ФСП — платформа получит его подтверждённые результаты.</p>
<input id="q" placeholder="Поиск по ФИО или FSP ID" oninput="f()" autofocus>
<ul id="list">{''.join(r[1] for r in rows)}</ul></div>
<script>function f(){{var q=document.getElementById('q').value.toLowerCase();document.querySelectorAll('#list li').forEach(function(li){{li.style.display=li.dataset.q.indexOf(q)>=0?'':'none'}})}}</script>
</body></html>"""
    return HTMLResponse(page, headers=fsp_link.PRIVATE_HEADERS)


@router.get("/fsp/callback", summary="Возврат от FSP ID (конец OIDC)",
            description="Обменивает code на утверждения (sub = FSP ID), создаёт ExternalIdentity(provider='fsp') и импортирует "
                        "VerifiedResult(source='fsp') через profile.import_results. Перенаправляет в профиль кандидата.",
            response_class=RedirectResponse, status_code=302, responses=responses(400, 409))
async def fsp_callback(code: str, state: str, binding: str | None = Cookie(None, alias=fsp_link.COOKIE_NAME),
                       session: AsyncSession = Depends(get_session)):
    uid = await fsp_link.user_for_state(session, state, binding, consume=True)
    user = await session.get(User, uid)
    if user is None or user.role != "candidate":
        raise ApiError(403, "forbidden", "Доступно только кандидату")
    claims = await fsp_oidc.exchange_code(code)
    if not claims:
        raise ApiError(400, "invalid_code", "FSP ID не подтвердил вход")
    sub = claims["sub"]
    other = (await session.execute(select(ExternalIdentity).where(
        ExternalIdentity.provider == "fsp", ExternalIdentity.subject == sub))).scalar_one_or_none()
    if other and other.user_id != uid:
        response = RedirectResponse(f"{config.FRONTEND_URL}/candidate/profile?fsp=conflict", status_code=302,
                                    headers=fsp_link.PRIVATE_HEADERS)
        response.delete_cookie(fsp_link.COOKIE_NAME, path=fsp_link.COOKIE_PATH)
        return response
    await link_fsp(session, uid, claims)
    await session.commit()
    response = RedirectResponse(f"{config.FRONTEND_URL}/candidate/profile?fsp=linked", status_code=302,
                                headers=fsp_link.PRIVATE_HEADERS)
    response.delete_cookie(fsp_link.COOKIE_NAME, path=fsp_link.COOKIE_PATH)
    return response


async def link_fsp(session: AsyncSession, user_id: int, claims: dict) -> list[dict]:
    """Связать внешнюю учётную запись и (пере)импортировать подтверждённые результаты источника fsp."""
    p = await session.get(CandidateProfile, user_id)
    if p:
        p.fsp_skipped = False
    await session.execute(delete(ExternalIdentity).where(ExternalIdentity.user_id == user_id, ExternalIdentity.provider == "fsp"))
    session.add(ExternalIdentity(user_id=user_id, provider="fsp", subject=claims["sub"], linked_at=utcnow(),
                                 claims={k: claims.get(k) for k in ("sub", "name", "email", "iss")}))
    await session.execute(delete(VerifiedResult).where(VerifiedResult.user_id == user_id, VerifiedResult.source == "fsp"))
    results = profile_svc.import_results("fsp", claims, fsp_oidc.registry())
    for r in results:
        session.add(VerifiedResult(user_id=user_id, **r))
    return results
