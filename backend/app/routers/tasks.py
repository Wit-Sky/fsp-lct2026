"""Регулярные короткие задания от работодателей (ТЗ 2.1, дополнительный функционал).

Работодатель публикует задачу для специализации (и, если нужно, грейда); система предлагает её подходящим кандидатам;
кандидат решает или предлагает подход; работодатель оценивает ответ. Свежий ответ поддерживает актуальность профиля:
фактор freshness в подборке считается от более позднего из теста и последнего ответа на задание.
Контакты кандидата здесь не раскрываются — только имя и грейд, как в подборке.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import candidate, employer
from app.db import get_session, utcnow
from app.errors import ApiError, not_found, responses
from app.models import CandidateProfile, Category, Employer, Task, TaskAnswer, User
from app.schemas import MyTasksOut, TaskAnswerIn, TaskAnswerOut, TaskIn, TaskOut, TaskReviewIn

OFFER_LIMIT = 3          # сколько заданий предлагать кандидату одновременно

employer_router = APIRouter(tags=["tasks"], responses=responses(401, 403))   # только для работодателя
candidate_router = APIRouter(tags=["tasks"], responses=responses(401, 403))  # только для кандидата


async def _task_out(session: AsyncSession, t: Task, answers: int = 0) -> dict:
    emp = await session.get(Employer, t.employer_id)
    return {"id": t.id, "title": t.title, "text": t.text, "spec": t.spec, "grade": t.grade, "kind": t.kind,
            "active": t.active, "company": emp.name if emp else "", "created_at": t.created_at, "answers": answers}


async def _answer_out(session: AsyncSession, a: TaskAnswer, with_candidate: bool) -> dict:
    t = await session.get(Task, a.task_id)
    out = {"id": a.id, "task_id": a.task_id, "task_title": t.title if t else "", "candidate_id": a.candidate_id,
           "answer": a.answer, "rating": a.rating, "feedback": a.feedback, "created_at": a.created_at,
           "reviewed_at": a.reviewed_at}
    if with_candidate:
        p = await session.get(CandidateProfile, a.candidate_id)
        cat = (await session.execute(select(Category).where(Category.user_id == a.candidate_id,
                                                             Category.spec == (t.spec if t else None)))).scalar_one_or_none()
        out["candidate_name"] = p.full_name if p and (p.visible_fields or {}).get("full_name") is not False else None
        out["candidate_grade"] = cat.grade if cat else None
    return out


async def _own_task(session: AsyncSession, task_id: int, emp: Employer) -> Task:
    t = await session.get(Task, task_id)
    if t is None or t.employer_id != emp.id:
        raise not_found("Задание")
    return t


# ---------------------------------------------------------------- работодатель

@employer_router.post("/tasks", response_model=TaskOut, status_code=201, summary="Опубликовать регулярное задание",
                      description="Короткая задача для кандидатов специализации (и грейда, если указан): решить её или "
                                  "предложить подход. Система предлагает задание подходящим кандидатам.",
                      responses=responses(422))
async def create_task(body: TaskIn, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    t = Task(employer_id=emp.id, **body.model_dump())
    session.add(t)
    await session.commit()
    return await _task_out(session, t)


@employer_router.get("/employer/tasks", response_model=list[TaskOut], summary="Мои регулярные задания",
                     description="Задания компании, новые сверху, с числом полученных ответов.")
async def my_tasks(emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Task).where(Task.employer_id == emp.id).order_by(Task.created_at.desc()))).scalars().all()
    counts = dict((await session.execute(select(TaskAnswer.task_id, func.count()).where(
        TaskAnswer.task_id.in_([t.id for t in rows])).group_by(TaskAnswer.task_id))).all()) if rows else {}
    return [await _task_out(session, t, counts.get(t.id, 0)) for t in rows]


@employer_router.post("/tasks/{task_id}/close", response_model=TaskOut, summary="Снять задание",
                      description="Задание перестаёт предлагаться кандидатам; полученные ответы сохраняются.",
                      responses=responses(404))
async def close_task(task_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    t = await _own_task(session, task_id, emp)
    t.active = False
    await session.commit()
    return await _task_out(session, t)


@employer_router.get("/tasks/{task_id}/answers", response_model=list[TaskAnswerOut], summary="Ответы на задание",
                     description="Ответы кандидатов на задание своей компании: имя (если кандидат его не скрыл), грейд, "
                                 "текст ответа и оценка. Контакты здесь не раскрываются — для связи нужно приглашение.",
                     responses=responses(404))
async def task_answers(task_id: int, emp: Employer = Depends(employer), session: AsyncSession = Depends(get_session)):
    await _own_task(session, task_id, emp)
    rows = (await session.execute(select(TaskAnswer).where(TaskAnswer.task_id == task_id)
                                  .order_by(TaskAnswer.created_at.desc()))).scalars().all()
    return [await _answer_out(session, a, with_candidate=True) for a in rows]


@employer_router.post("/task-answers/{answer_id}/review", response_model=TaskAnswerOut, summary="Оценить ответ",
                      description="Оценка 0–3 и комментарий; кандидат видит их в своих заданиях.", responses=responses(404, 422))
async def review_answer(answer_id: int, body: TaskReviewIn, emp: Employer = Depends(employer),
                        session: AsyncSession = Depends(get_session)):
    a = await session.get(TaskAnswer, answer_id)
    if a is None:
        raise not_found("Ответ")
    await _own_task(session, a.task_id, emp)
    a.rating, a.feedback, a.reviewed_at = body.rating, body.feedback, utcnow()
    await session.commit()
    return await _answer_out(session, a, with_candidate=True)


# ---------------------------------------------------------------- кандидат

async def _candidate_grades(session: AsyncSession, user: User) -> dict[str, str | None]:
    """Специализации кандидата → грейд категории (None, если теста по специализации ещё нет)."""
    grades: dict[str, str | None] = {c.spec: c.grade for c in (await session.execute(
        select(Category).where(Category.user_id == user.id))).scalars()}
    p = await session.get(CandidateProfile, user.id)
    if p and p.spec and p.spec not in grades:
        grades[p.spec] = None
    return grades


@candidate_router.get("/me/tasks", response_model=MyTasksOut, summary="Мои регулярные задания",
                      description=f"До {OFFER_LIMIT} свежих заданий работодателей по специализации и грейду кандидата, "
                                  "на которые он ещё не ответил, и история своих ответов с оценками.")
async def my_candidate_tasks(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    grades = await _candidate_grades(session, user)
    answered = (await session.execute(select(TaskAnswer).where(TaskAnswer.candidate_id == user.id)
                                      .order_by(TaskAnswer.created_at.desc()))).scalars().all()
    done = {a.task_id for a in answered}
    offered = []
    if grades:
        rows = (await session.execute(select(Task).where(Task.active.is_(True), Task.spec.in_(list(grades)))
                                      .order_by(Task.created_at.desc(), Task.id.desc()))).scalars().all()
        for t in rows:
            if t.id in done or (t.grade is not None and grades.get(t.spec) not in (None, t.grade)):
                continue
            offered.append(await _task_out(session, t))
            if len(offered) >= OFFER_LIMIT:
                break
    hint = None if grades else "Укажите специализацию в профиле или пройдите тест — тогда появятся задания работодателей"
    return {"offered": offered, "answered": [await _answer_out(session, a, with_candidate=False) for a in answered],
            "hint": hint}


@candidate_router.post("/tasks/{task_id}/answer", response_model=TaskAnswerOut, status_code=201, summary="Ответить на задание",
                       description="Решение или подход к решению в свободной форме. Один ответ на задание; "
                                   "свежий ответ повышает фактор актуальности профиля в подборке.",
                       responses=responses(404, 409, 422))
async def answer_task(task_id: int, body: TaskAnswerIn, user: User = Depends(candidate),
                      session: AsyncSession = Depends(get_session)):
    t = await session.get(Task, task_id)
    grades = await _candidate_grades(session, user)
    if t is None or not t.active or t.spec not in grades:
        raise not_found("Задание")
    exists = (await session.execute(select(TaskAnswer).where(TaskAnswer.task_id == task_id,
                                                             TaskAnswer.candidate_id == user.id))).scalar_one_or_none()
    if exists:
        raise ApiError(409, "already_answered", "На это задание вы уже ответили")
    a = TaskAnswer(task_id=task_id, candidate_id=user.id, answer=body.answer)
    session.add(a)
    await session.commit()
    return await _answer_out(session, a, with_candidate=False)
