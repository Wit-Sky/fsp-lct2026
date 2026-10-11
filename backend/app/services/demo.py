"""Новый демовход начинает чистый путь; обычные пользователи не затрагиваются."""
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import utcnow
from app.models import (Application, CandidateProfile, Category, ExternalIdentity, FspAuthorization,
                        GradeAttempt, Invitation, TaskAnswer, User, VerifiedResult)


async def reset_candidate(session: AsyncSession, user: User) -> None:
    if not user.is_demo or user.role != "candidate":
        return
    for model, key in (
        (FspAuthorization, FspAuthorization.user_id),
        (ExternalIdentity, ExternalIdentity.user_id),
        (VerifiedResult, VerifiedResult.user_id),
        (GradeAttempt, GradeAttempt.user_id),
        (Category, Category.user_id),
        (Invitation, Invitation.candidate_id),
        (Application, Application.candidate_id),
        (TaskAnswer, TaskAnswer.candidate_id),
    ):
        await session.execute(delete(model).where(key == user.id))
    p = await session.get(CandidateProfile, user.id)
    if p is None:
        p = CandidateProfile(user_id=user.id)
        session.add(p)
    defaults = dict(full_name="Демо Кандидат", birth_date=None, city="Москва", work_format="hybrid",
                    salary_expect_from=150000, spec=None, skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                    roles=[], soft_skills=[], experience_years=2,
                    about="Демо-аккаунт для жюри: без теста и без истории ФСП.",
                    phone="+7 900 000-00-00", telegram="@demo_candidate", consent_pd=True,
                    parent_consent=False, fsp_skipped=False, visible_fields={})
    for key, value in defaults.items():
        setattr(p, key, value)
    p.updated_at = utcnow()
