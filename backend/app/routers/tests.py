"""Тестирование на грейд: роутер тонкий — состояние попытки хранит БД, логика в services/testing."""
import copy
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app import config
from app.auth import candidate
from app.catalog import GRADES
from app.db import aware, get_session, utcnow
from app.errors import ApiError, not_found, responses
from app.models import CandidateProfile, Category, GradeAttempt, User
from app.schemas import AnswerIn, CategoryOut, TestResultOut, TestStartIn, TestStateOut
from app.services import matching, testing

router = APIRouter(tags=["tests"], responses=responses(401, 403))  # все методы — только для кандидата
GRACE = timedelta(seconds=15)        # запас на сетевые задержки к лимиту 5 минут


def _deadline(a: GradeAttempt) -> datetime:
    return aware(a.started_at) + config.TEST_TIME_LIMIT


def _state_out(a: GradeAttempt) -> dict:
    state = a.items
    finished = a.finished_at is not None
    item = None if finished else testing.public_item(state.get("current"), state)
    return {"attempt_id": a.id, "spec": a.spec, "claimed_grade": a.claimed_grade, "item": item, "finished": finished,
            "answered": len(state["responses"]), "total": state["n_items"], "deadline": _deadline(a),
            "item_time_limit_sec": int(config.ITEM_TIME_LIMIT.total_seconds()),
            "result": state.get("result") if finished else None}


async def last_finished(session: AsyncSession, user_id: int, spec: str) -> GradeAttempt | None:
    return (await session.execute(select(GradeAttempt).where(
        GradeAttempt.user_id == user_id, GradeAttempt.spec == spec, GradeAttempt.finished_at.is_not(None))
        .order_by(GradeAttempt.finished_at.desc()).limit(1))).scalar_one_or_none()


def _last_dict(a: GradeAttempt | None) -> dict | None:
    if a is None:
        return None
    return {"claimed_grade": a.claimed_grade, "result": a.result, "finished_at": aware(a.finished_at)}


async def finalize(session: AsyncSession, a: GradeAttempt, now: datetime) -> dict:
    """Завершить попытку и обновить категорию. Грейд не понижается принудительно: подтверждённая категория
    сохраняется при провале теста на более высокий грейд."""
    state = copy.deepcopy(a.items)
    res = testing.finish(state)                    # текущее и оставшиеся задания засчитываются неверными
    a.theta, a.finished_at = res["theta"], now
    a.result = "confirmed" if res["confirmed"] else "failed"
    state["result"] = res
    a.items = state
    flag_modified(a, "items")
    cat = (await session.execute(select(Category).where(Category.user_id == a.user_id, Category.spec == a.spec))).scalar_one_or_none()
    if cat is None:
        cat = Category(user_id=a.user_id, spec=a.spec, grade=a.claimed_grade, status="none")
        session.add(cat)
    if res["confirmed"]:
        cat.grade, cat.status, cat.theta = a.claimed_grade, "confirmed", res["theta"]
        cat.confirmed_at, cat.tested_at, cat.suggest_upgrade = now, now, res["suggest_upgrade"]
    elif cat.status != "confirmed":
        cat.grade, cat.status, cat.theta, cat.tested_at, cat.suggest_upgrade = a.claimed_grade, "unconfirmed", res["theta"], now, False
    cat.next_attempt_at = now + config.cooldown()
    prof = await session.get(CandidateProfile, a.user_id)
    if prof is not None and not prof.spec:
        prof.spec = a.spec
    return res


@router.post("/tests/start", response_model=TestStateOut, status_code=201, summary="Начать тест на грейд",
             description="Экспресс-тест: 10 заданий за 5 минут. Первые 3 — около порога заявленного грейда, дальше адаптивно. "
                         "Варианты уникальны для кандидата и попытки. 403 cooldown — повтор на тот же или более высокий грейд "
                         "раньше срока (в ответе next_attempt_at); на грейд ниже после провала — сразу. Незавершённая попытка "
                         "по той же специализации продолжается.", responses=responses(403, 409, 422))
async def start(body: TestStartIn, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    now = utcnow()
    if not testing.has_bank(body.spec):
        raise ApiError(409, "bank_not_ready", "Банк заданий по этой специализации ещё не готов")
    active = (await session.execute(select(GradeAttempt).where(
        GradeAttempt.user_id == user.id, GradeAttempt.spec == body.spec, GradeAttempt.finished_at.is_(None))
        .order_by(GradeAttempt.started_at.desc()))).scalars().all()
    for a in active:
        if now <= _deadline(a) + GRACE and a.claimed_grade == body.claimed_grade:
            return _state_out(a)
        await finalize(session, a, min(now, _deadline(a)))
    await session.flush()
    until = testing.cooldown_until(_last_dict(await last_finished(session, user.id, body.spec)), body.claimed_grade, config.cooldown())
    if until and until > now:
        await session.commit()
        raise ApiError(403, "cooldown", f"Повторный тест на этот грейд будет доступен {until:%d.%m.%Y %H:%M} UTC",
                       next_attempt_at=until.isoformat())
    n = (await session.execute(select(func.count()).select_from(GradeAttempt).where(
        GradeAttempt.user_id == user.id, GradeAttempt.spec == body.spec))).scalar_one()
    state = testing.build_attempt(user.id, body.spec, body.claimed_grade, n + 1)
    testing.next_item(state)
    state["issued_at"] = now.isoformat()
    a = GradeAttempt(user_id=user.id, spec=body.spec, claimed_grade=body.claimed_grade, attempt_no=n + 1,
                     started_at=now, items=state)
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return _state_out(a)


async def _own_attempt(session: AsyncSession, attempt_id: int, user: User) -> GradeAttempt:
    a = await session.get(GradeAttempt, attempt_id)
    if a is None or a.user_id != user.id:
        raise not_found("Попытка")
    return a


@router.get("/tests/{attempt_id}", response_model=TestStateOut, summary="Текущее состояние попытки",
            description="Текущее задание (без ответа) — чтобы продолжить тест после перезагрузки страницы.",
            responses=responses(404))
async def get_state(attempt_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    a = await _own_attempt(session, attempt_id, user)
    if a.finished_at is None and utcnow() > _deadline(a) + GRACE:
        await finalize(session, a, _deadline(a))
        await session.commit()
    return _state_out(a)


@router.post("/tests/{attempt_id}/answer", response_model=TestStateOut, summary="Ответить на задание",
             description="Принимает ответ на текущее задание и возвращает следующее или итог. Время проверяет сервер: "
                         "ответ позже лимита на задание засчитывается неверным, после 5 минут тест завершается.",
             responses=responses(404, 409))
async def answer(attempt_id: int, body: AnswerIn, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    now = utcnow()
    a = await _own_attempt(session, attempt_id, user)
    if a.finished_at is not None:
        raise ApiError(409, "finished", "Тест уже завершён")
    if now > _deadline(a) + GRACE:
        await finalize(session, a, _deadline(a))
        await session.commit()
        return _state_out(a)
    state = copy.deepcopy(a.items)
    issued = datetime.fromisoformat(state.get("issued_at")) if state.get("issued_at") else aware(a.started_at)
    late = now - issued > config.ITEM_TIME_LIMIT + GRACE
    try:
        testing.submit(state, body.item_id, body.answer, late=late)
    except ValueError:
        raise ApiError(409, "item_not_current", "Это задание уже не текущее — запросите состояние попытки")
    nxt = testing.next_item(state)
    state["issued_at"] = now.isoformat()
    a.items = state
    flag_modified(a, "items")
    if nxt is None:
        await finalize(session, a, now)
    await session.commit()
    return _state_out(a)


@router.get("/tests/{attempt_id}/result", response_model=TestResultOut, summary="Итог теста",
            description="θ (шкала Раша), подтверждён ли грейд, предложение пройти тест на повышение, разбор по темам.",
            responses=responses(404, 409))
async def result(attempt_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    a = await _own_attempt(session, attempt_id, user)
    if a.finished_at is None:
        if utcnow() > _deadline(a) + GRACE:
            await finalize(session, a, _deadline(a))
            await session.commit()
        else:
            raise ApiError(409, "not_finished", "Тест ещё не завершён")
    res = a.items["result"]
    cat = (await session.execute(select(Category).where(Category.user_id == user.id, Category.spec == a.spec))).scalar_one_or_none()
    return {"attempt_id": a.id, "spec": a.spec, "claimed_grade": a.claimed_grade, "theta": res["theta"], "grade": res["grade"],
            "confirmed": res["confirmed"], "suggest_upgrade": res["suggest_upgrade"], "correct": res["correct"],
            "total": res["total"], "topics": res["topics"],
            "category": {"spec": cat.spec, "grade": cat.grade, "status": cat.status, "theta": cat.theta} if cat else None,
            "next_attempt_at": aware(cat.next_attempt_at) if cat else None,
            "started_at": aware(a.started_at), "finished_at": aware(a.finished_at)}


@router.get("/me/category", response_model=CategoryOut, summary="Моя категория и история попыток",
            description="Текущая категория (специализация + грейд + статус), процентиль θ в категории, история попыток и "
                        "когда можно пройти тест на каждый грейд (can_retest).", responses=responses(401))
async def my_category(spec: str | None = None, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    prof = await session.get(CandidateProfile, user.id)
    cats = (await session.execute(select(Category).where(Category.user_id == user.id))).scalars().all()
    spec = spec or (prof.spec if prof else None) or (cats[0].spec if cats else None)
    cat = next((c for c in cats if c.spec == spec), None)
    attempts = (await session.execute(select(GradeAttempt).where(GradeAttempt.user_id == user.id)
                                      .order_by(GradeAttempt.started_at.desc()))).scalars().all()
    pct = None
    if cat and cat.theta is not None:
        pop = (await session.execute(select(Category.theta).where(Category.spec == cat.spec, Category.grade == cat.grade,
                                                                   Category.theta.is_not(None)))).scalars().all()
        pct = round(matching.percentile(cat.theta, list(pop)), 3)
    can = {}
    if spec:
        last = _last_dict(await last_finished(session, user.id, spec))
        now = utcnow()
        for g in GRADES:
            until = testing.cooldown_until(last, g, config.cooldown())
            can[g] = until if until and until > now else None
    return {"spec": spec, "grade": cat.grade if cat else None, "status": cat.status if cat else "none",
            "theta": cat.theta if cat else None, "percentile": pct,
            "confirmed_at": aware(cat.confirmed_at) if cat else None, "tested_at": aware(cat.tested_at) if cat else None,
            "next_attempt_at": aware(cat.next_attempt_at) if cat else None,
            "suggest_upgrade": bool(cat.suggest_upgrade) if cat else False, "can_retest": can,
            "attempts": [{"id": x.id, "spec": x.spec, "claimed_grade": x.claimed_grade, "started_at": aware(x.started_at),
                          "finished_at": aware(x.finished_at), "theta": x.theta, "result": x.result} for x in attempts]}
