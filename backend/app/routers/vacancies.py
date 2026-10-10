"""Вакансии и отклики со стороны кандидата (дополнительный сценарий)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.auth import candidate
from app.catalog import ALL_SKILLS, GRADE_TITLES, GRADES, SALARY_TYPES, SKILLS, SPECS, THRESHOLDS, WORK_FORMATS, FSP_DISCIPLINES
from app.db import get_session
from app.errors import ApiError, not_found, responses
from app.models import Application, Employer, Need, User
from app.routers.employer import application_out
from app.schemas import ApplicationOut, ApplyIn, VacancyOut

router = APIRouter(tags=["vacancies"])


async def _vacancy_out(session: AsyncSession, n: Need, applied: set[int]) -> dict:
    emp = await session.get(Employer, n.employer_id)
    return {**repo.need_dict(n), "company": emp.name if emp else "", "applied": n.id in applied}


@router.get("/vacancies", response_model=list[VacancyOut], summary="Опубликованные вакансии",
            description="Зарплата от–до видна до начала общения. Фильтры: специализация, грейд.")
async def vacancies(spec: str | None = None, grade: str | None = None, user: User = Depends(candidate),
                    session: AsyncSession = Depends(get_session)):
    q = select(Need).where(Need.published.is_(True))
    if spec:
        q = q.where(Need.spec == spec)
    if grade:
        q = q.where(Need.grade == grade)
    rows = (await session.execute(q.order_by(Need.created_at.desc()))).scalars().all()
    applied = set((await session.execute(select(Application.need_id).where(Application.candidate_id == user.id))).scalars())
    return [await _vacancy_out(session, n, applied) for n in rows]


@router.get("/vacancies/{need_id}", response_model=VacancyOut, summary="Вакансия", responses=responses(404))
async def vacancy(need_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    n = await session.get(Need, need_id)
    if n is None or not n.published:
        raise not_found("Вакансия")
    applied = set((await session.execute(select(Application.need_id).where(Application.candidate_id == user.id))).scalars())
    return await _vacancy_out(session, n, applied)


@router.post("/vacancies/{need_id}/apply", response_model=ApplicationOut, status_code=201, summary="Откликнуться",
             description="Самостоятельный отклик: работодатель сразу видит контакты кандидата.", responses=responses(404, 409))
async def apply(need_id: int, body: ApplyIn | None = None, user: User = Depends(candidate),
                session: AsyncSession = Depends(get_session)):
    n = await session.get(Need, need_id)
    if n is None or not n.published:
        raise not_found("Вакансия")
    exists = (await session.execute(select(Application).where(
        Application.need_id == need_id, Application.candidate_id == user.id))).scalar_one_or_none()
    if exists:
        raise ApiError(409, "already_applied", "Вы уже откликнулись на эту вакансию")
    a = Application(need_id=need_id, candidate_id=user.id, message=body.message if body else None, status="sent")
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return await application_out(session, a, with_card=False)


@router.get("/me/applications", response_model=list[ApplicationOut], summary="Мои отклики и их статусы")
async def my_applications(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Application).where(Application.candidate_id == user.id)
                                  .order_by(Application.created_at.desc()))).scalars().all()
    return [await application_out(session, a, with_card=False) for a in rows]


catalog_router = APIRouter(tags=["catalog"])


@catalog_router.get("/catalog", summary="Справочники",
                    description="Специализации, грейды и пороги θ, навыки по специализациям, форматы работы, дисциплины ФСП.")
async def catalog():
    return {"specs": [{"id": k, "title": v} for k, v in SPECS.items()],
            "grades": [{"id": g, "title": GRADE_TITLES[g], "threshold": THRESHOLDS[g]} for g in GRADES],
            "skills": SKILLS, "all_skills": ALL_SKILLS, "work_formats": WORK_FORMATS, "salary_types": SALARY_TYPES,
            "fsp_disciplines": FSP_DISCIPLINES}
