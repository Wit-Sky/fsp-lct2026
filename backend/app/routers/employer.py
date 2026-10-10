"""Кабинет работодателя: профиль компании, потребности, подборка с объяснением, поиск по банку, приглашения."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.auth import employer
from app.db import aware, get_session, utcnow
from app.errors import ApiError, not_found, responses
from app.models import Application, Employer, Invitation, Need, User
from app.schemas import (ApplicationOut, ApplicationStatusIn, CandidateCard, CategoryCount, EmployerIn, EmployerOut,
                         InvitationIn, InvitationOut, MatchesOut, NeedCreated, NeedIn, NeedOut)
from app.services import matching, profile as profile_svc

router = APIRouter(tags=["employer"], responses=responses(401, 403))  # все методы — только для работодателя


@router.get("/employer", response_model=EmployerOut, summary="Профиль компании",
            description="Профиль компании текущего работодателя: название, ИНН, сфера, описание, контакты для кандидатов.")
async def get_employer(emp: Employer = Depends(employer)):
    return emp


@router.put("/employer", response_model=EmployerOut, summary="Изменить профиль компании",
            description="Передаются только изменяемые поля.", responses=responses(422))
async def put_employer(body: EmployerIn, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    emp = await session.merge(emp)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(emp, k, v)
    await session.commit()
    return emp


# ---------------------------------------------------------------- потребности

async def _own_need(session: AsyncSession, need_id: int, emp: Employer) -> Need:
    n = await session.get(Need, need_id)
    if n is None or n.employer_id != emp.id:
        raise not_found("Потребность")
    return n


@router.post("/needs", response_model=NeedCreated, status_code=201, summary="Описать потребность",
             description="Какие специалисты нужны: специализация, грейд, стек с весами, зарплата от–до (обязательно, рубли, gross/net). "
                          "Возвращает search_id — подборку по нему можно уточнять фильтрами без потери исходного запроса.",
             responses=responses(422))
async def create_need(body: NeedIn, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    n = Need(employer_id=emp.id, **{**body.model_dump(), "skills": [s.model_dump() for s in body.skills]})
    session.add(n)
    await session.commit()
    await session.refresh(n)
    return {**repo.need_dict(n), "search_id": n.id}


@router.get("/employer/needs", response_model=list[NeedOut], summary="Мои потребности и вакансии",
            description="Все потребности компании, новые сверху; published = true — опубликована как вакансия.")
async def my_needs(emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Need).where(Need.employer_id == emp.id).order_by(Need.created_at.desc()))).scalars().all()
    return [repo.need_dict(n) for n in rows]


@router.get("/needs/{need_id}", response_model=NeedOut, summary="Потребность",
            description="Потребность своей компании; чужая — 404.", responses=responses(404))
@router.get("/searches/{need_id}", response_model=NeedOut, summary="Исходный запрос подборки (search_id = id потребности)",
            description="Исходный запрос сохраняется: уточнение фильтров подборки (параметры /matches) его не сбрасывает.",
            responses=responses(404))
async def get_need(need_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    return repo.need_dict(await _own_need(session, need_id, emp))


@router.put("/needs/{need_id}", response_model=NeedOut, summary="Изменить потребность / вакансию",
            description="Полная замена полей; зарплата от–до обязательна.", responses=responses(404, 422))
async def put_need(need_id: int, body: NeedIn, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    n = await _own_need(session, need_id, emp)
    for k, v in body.model_dump().items():
        setattr(n, k, v if k != "skills" else [s.model_dump() for s in body.skills])
    await session.commit()
    return repo.need_dict(n)


@router.post("/needs/{need_id}/publish", response_model=NeedOut, summary="Опубликовать как вакансию",
             description="published=true — потребность видна кандидатам в списке вакансий (дополнительный сценарий отклика).",
             responses=responses(404))
async def publish(need_id: int, published: bool = True, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    n = await _own_need(session, need_id, emp)
    n.published = published
    await session.commit()
    return repo.need_dict(n)


@router.get("/needs/{need_id}/categories", response_model=list[CategoryCount], summary="Подходящие категории",
            description="Категории (специализация + грейд) для потребности с числом кандидатов: целевая и соседние.",
            responses=responses(404))
async def need_categories(need_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    n = await _own_need(session, need_id, emp)
    cands = await repo.load_candidates(session, spec=n.spec)
    return matching.category_counts(repo.need_dict(n), cands)


@router.get("/needs/{need_id}/matches", response_model=MatchesOut, summary="Подборка кандидатов с объяснением",
            description="Жёсткий фильтр по категории, затем скор 0–100: 0,40·стек + 0,30·тест (процентиль θ в категории) + "
                        "0,15·ФСП + 0,10·свежесть + 0,05·условия; ×0,6, если грейд не подтверждён. explain — вклад каждого фактора. "
                        "Контакты скрыты, пока кандидат не принял приглашение или не откликнулся сам.", responses=responses(404))
async def need_matches(need_id: int, grade_adj: bool = Query(False, description="Включить соседние грейды"),
                       fsp_only: bool = Query(False, description="Только с подтверждёнными результатами ФСП"),
                       skills: str | None = Query(None, description="Уточнение: обязательные навыки через запятую"),
                       limit: int = Query(50, ge=1, le=300),
                       emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    n = await _own_need(session, need_id, emp)
    extra = [s.strip() for s in (skills or "").split(",") if s.strip()]
    cands = repo.with_percentiles(await repo.load_candidates(session, spec=n.spec))
    ranked = matching.rank(repo.need_dict(n), cands, grade_adj=grade_adj, fsp_only=fsp_only, extra_skills=extra, limit=limit)
    visible = await repo.visible_contacts(session, emp.id)
    inv = await repo.invitation_statuses(session, emp.id)
    by_id = {c["id"]: c for c in cands}
    items = [{**r, "candidate": repo.card(by_id[r["candidate_id"]], r["candidate_id"] in visible, inv.get(r["candidate_id"]))}
             for r in ranked]
    return {"need_id": n.id, "search_id": n.id, "total": len(items), "items": items,
            "filters": {"grade_adj": grade_adj, "fsp_only": fsp_only, "skills": extra, "limit": limit}}


# ---------------------------------------------------------------- банк кандидатов

@router.get("/candidates", response_model=list[CandidateCard], summary="Поиск по банку кандидатов",
            description="Фильтры: специализация, грейд, стек (все перечисленные навыки), наличие ФСП, статус грейда. "
                        "Сортировка: подтверждённые выше, затем по θ.")
async def search_candidates(spec: str | None = None, grade: str | None = None, skills: str | None = None,
                            fsp: bool | None = None, status: str | None = None, q: str | None = None,
                            limit: int = Query(50, ge=1, le=300), offset: int = Query(0, ge=0),
                            emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    cands = await repo.load_candidates(session, spec=spec)
    need = {s.strip().lower() for s in (skills or "").split(",") if s.strip()}
    out = []
    for c in cands:
        if grade and c["grade"] != grade:
            continue
        if status and c["status"] != status:
            continue
        if fsp is not None and bool(c["results"]) != fsp:
            continue
        if need and not need <= {s.lower() for s in c["skills"]}:
            continue
        if q and q.lower() not in f"{c['full_name']} {c['about'] or ''} {c['city'] or ''}".lower():
            continue
        out.append(c)
    repo.with_percentiles(out, cands)
    out.sort(key=lambda c: (c["status"] != "confirmed", -(c["theta"] if c["theta"] is not None else -9), c["id"]))
    visible = await repo.visible_contacts(session, emp.id)
    inv = await repo.invitation_statuses(session, emp.id)
    return [repo.card(c, c["id"] in visible, inv.get(c["id"])) for c in out[offset:offset + limit]]


@router.get("/candidates/{cand_id}", response_model=CandidateCard, summary="Карточка кандидата",
            description="Контакты (email, телефон, Telegram) — только если кандидат принял приглашение этой компании "
                        "или откликнулся на её вакансию; иначе null и contacts_hidden = true.", responses=responses(404))
async def candidate_card(cand_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    found = await repo.load_candidates(session, ids=[cand_id], with_category_only=False)
    if not found:
        raise not_found("Кандидат")
    c = found[0]
    if c["grade"]:
        pop = await repo.load_candidates(session, spec=c["spec"])
        repo.with_percentiles([c], [x for x in pop if x["grade"] == c["grade"]])
    visible = await repo.visible_contacts(session, emp.id)
    inv = await repo.invitation_statuses(session, emp.id)
    return repo.card(c, cand_id in visible, inv.get(cand_id))


# ---------------------------------------------------------------- приглашения (сторона работодателя)

@router.post("/invitations", response_model=InvitationOut, status_code=201, summary="Пригласить кандидата",
             description="Адресное приглашение: описание предложения, зарплата от–до в рублях (обязательно, gross/net), способ связи. "
                         "Привязка к потребности необязательна.", responses=responses(404, 409, 422))
async def invite(body: InvitationIn, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    found = await repo.load_candidates(session, ids=[body.candidate_id], with_category_only=False)
    if not found:
        raise not_found("Кандидат")
    if body.need_id is not None:
        await _own_need(session, body.need_id, emp)
    dup = (await session.execute(select(Invitation).where(
        Invitation.employer_id == emp.id, Invitation.candidate_id == body.candidate_id,
        Invitation.need_id.is_(None) if body.need_id is None else Invitation.need_id == body.need_id,
        Invitation.status.in_(["sent", "viewed"])))).scalar_one_or_none()
    if dup:
        raise ApiError(409, "already_invited", "Приглашение этому кандидату уже отправлено и ждёт ответа")
    inv = Invitation(employer_id=emp.id, **body.model_dump(), status="sent")
    session.add(inv)
    await session.commit()
    await session.refresh(inv)
    return await repo.invitation_out(session, inv, for_employer=True)


@router.get("/employer/invitations", response_model=list[InvitationOut], summary="Мои приглашения и их статусы",
            description="sent → viewed → accepted | declined. У принятых — контакты кандидата.")
async def employer_invitations(emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Invitation).where(Invitation.employer_id == emp.id)
                                  .order_by(Invitation.updated_at.desc()))).scalars().all()
    return [await repo.invitation_out(session, i, for_employer=True) for i in rows]


# ---------------------------------------------------------------- отклики на вакансии (сторона работодателя)

async def application_out(session: AsyncSession, a: Application, with_card: bool) -> dict:
    n = await session.get(Need, a.need_id)
    emp = await session.get(Employer, n.employer_id)
    out = {"id": a.id, "need_id": a.need_id, "need_title": n.title, "company": emp.name, "candidate_id": a.candidate_id,
           "message": a.message, "status": a.status, "created_at": aware(a.created_at), "updated_at": aware(a.updated_at),
           "salary_from": n.salary_from, "salary_to": n.salary_to, "salary_type": n.salary_type, "candidate": None}
    if with_card:
        found = await repo.load_candidates(session, ids=[a.candidate_id], only_published=False, with_category_only=False)
        if found:
            out["candidate"] = repo.card(found[0], contacts_visible=True)   # кандидат откликнулся сам
    return out


@router.get("/needs/{need_id}/applications", response_model=list[ApplicationOut], summary="Отклики на вакансию",
            description="Кандидат откликнулся сам — контакты видны.", responses=responses(404))
async def need_applications(need_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    await _own_need(session, need_id, emp)
    rows = (await session.execute(select(Application).where(Application.need_id == need_id)
                                  .order_by(Application.created_at.desc()))).scalars().all()
    out = []
    for a in rows:
        if a.status == "sent":
            a.status, a.updated_at = "viewed", utcnow()
        out.append(await application_out(session, a, with_card=True))
    await session.commit()
    return out


@router.post("/applications/{app_id}/status", response_model=ApplicationOut, summary="Ответить на отклик",
             description="viewed | accepted | declined.", responses=responses(404))
async def application_status(app_id: int, body: ApplicationStatusIn, emp: Employer = Depends(employer),
                             session: AsyncSession = Depends(get_session)):
    a = await session.get(Application, app_id)
    if a is None:
        raise not_found("Отклик")
    await _own_need(session, a.need_id, emp)
    a.status, a.updated_at = body.status, utcnow()
    await session.commit()
    return await application_out(session, a, with_card=True)
