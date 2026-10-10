"""Кабинет кандидата: профиль, резюме, PDF-профиль, подтверждённые результаты, приглашения."""
import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.auth import candidate
from app.db import get_session, utcnow
from app.errors import ApiError, not_found, responses
from app.models import CandidateProfile, ExternalIdentity, Invitation, User, VerifiedResult
from app.schemas import InvitationOut, ProfileIn, ProfileOut, ResultsOut, ResumeDraft
from app.services import profile as profile_svc

router = APIRouter(tags=["candidate"], responses=responses(401, 403))  # все методы — только для кандидата


async def _profile(session: AsyncSession, user: User) -> CandidateProfile:
    p = await session.get(CandidateProfile, user.id)
    if p is None:
        p = CandidateProfile(user_id=user.id, full_name="", skills=[], visible_fields={})
        session.add(p)
        await session.flush()
    return p


async def _profile_out(session: AsyncSession, user: User, p: CandidateProfile) -> dict:
    ext = (await session.execute(select(ExternalIdentity).where(
        ExternalIdentity.user_id == user.id, ExternalIdentity.provider == "fsp"))).scalar_one_or_none()
    pd = {"consent_pd": p.consent_pd, "parent_consent": p.parent_consent, "birth_date": p.birth_date}
    return {"user_id": user.id, "email": user.email, "full_name": p.full_name or "", "birth_date": p.birth_date,
            "phone": p.phone, "telegram": p.telegram, "city": p.city, "work_format": p.work_format,
            "salary_expect_from": p.salary_expect_from, "spec": p.spec, "skills": list(p.skills or []),
            "experience_years": p.experience_years, "about": p.about, "consent_pd": p.consent_pd,
            "parent_consent": p.parent_consent, "visible_fields": dict(p.visible_fields or {}),
            "minor": profile_svc.is_minor(p.birth_date), "published": profile_svc.publishable(pd),
            "fsp_linked": ext is not None, "fsp_id": ext.subject if ext else None}


@router.get("/me/profile", response_model=ProfileOut, summary="Мой профиль",
            description="published — виден ли профиль работодателям (нужно согласие на обработку ПД; младше 18 — ещё и согласие родителя).")
async def get_profile(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    p = await _profile(session, user)
    await session.commit()
    return await _profile_out(session, user, p)


@router.put("/me/profile", response_model=ProfileOut, summary="Изменить профиль, согласия и приватность",
            description="Передаются только изменяемые поля. visible_fields — что видно работодателю.", responses=responses(422))
async def put_profile(body: ProfileIn, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    p = await _profile(session, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = utcnow()
    await session.commit()
    return await _profile_out(session, user, p)


@router.post("/me/resume/parse", response_model=ResumeDraft, summary="Разобрать PDF-резюме",
             description="pdfplumber извлекает текст, регулярные выражения и словарь навыков дают черновик полей. "
                         "Профиль не меняется — фронтенд показывает черновик для подтверждения.", responses=responses(422))
async def parse_resume(file: UploadFile = File(...), user: User = Depends(candidate)):
    import pdfplumber
    data = await file.read()
    if not data[:5] == b"%PDF-":
        raise ApiError(422, "not_pdf", "Нужен файл PDF")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:10])
    except Exception:
        raise ApiError(422, "bad_pdf", "Не удалось прочитать PDF")
    draft = profile_svc.parse_resume_text(text)
    return {**draft, "text_chars": len(text)}


@router.get("/me/profile.pdf", summary="Стандартизированный PDF-профиль", response_class=Response,
            description="PDF с профилем, категорией и подтверждёнными результатами в едином формате (reportlab, шрифт DejaVuSans).",
            responses={200: {"content": {"application/pdf": {}}, "description": "PDF"}})
async def profile_pdf(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    from app.pdf import render_profile
    cands = await repo.load_candidates(session, ids=[user.id], only_published=False, with_category_only=False)
    c = cands[0] if cands else {"full_name": "", "skills": [], "results": []}
    c["email"] = user.email
    pdf = render_profile(c)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="profile.pdf"'})


@router.get("/me/results", response_model=ResultsOut, summary="Мои подтверждённые результаты",
            description="Подтверждённые результаты по источникам (сейчас fsp). Нет истории ФСП — пустой список и явный текст в explain.")
async def my_results(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(VerifiedResult).where(VerifiedResult.user_id == user.id)
                                  .order_by(VerifiedResult.year.desc()))).scalars().all()
    p = await session.get(CandidateProfile, user.id)
    ext = (await session.execute(select(ExternalIdentity).where(
        ExternalIdentity.user_id == user.id, ExternalIdentity.provider == "fsp"))).scalar_one_or_none()
    by: dict[str, list] = {}
    for r in rows:
        by.setdefault(r.source, []).append(repo.result_dict(r))
    score, explain = profile_svc.fsp_score(by.get("fsp", []), (p.spec if p else None) or "backend")
    return {"sources": by, "fsp_linked": ext is not None, "fsp_score": score, "explain": explain}


@router.delete("/me/fsp", status_code=204, summary="Отвязать FSP ID",
               description="Удаляет внешнюю учётную запись и импортированные из неё подтверждённые результаты.")
async def unlink_fsp(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(ExternalIdentity).where(ExternalIdentity.user_id == user.id, ExternalIdentity.provider == "fsp"))
    await session.execute(delete(VerifiedResult).where(VerifiedResult.user_id == user.id, VerifiedResult.source == "fsp"))
    await session.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- приглашения (сторона кандидата)

@router.get("/me/invitations", response_model=list[InvitationOut], summary="Мои приглашения",
            description="Входящие приглашения: компания, предложение, зарплата от–до, способ связи, статус. Только свои.")
async def my_invitations(user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Invitation).where(Invitation.candidate_id == user.id)
                                  .order_by(Invitation.created_at.desc()))).scalars().all()
    return [await repo.invitation_out(session, i, for_employer=False) for i in rows]


async def _own_invitation(session: AsyncSession, inv_id: int, user: User) -> Invitation:
    inv = await session.get(Invitation, inv_id)
    if inv is None or inv.candidate_id != user.id:
        raise not_found("Приглашение")       # чужие приглашения неотличимы от несуществующих
    return inv


@router.get("/invitations/{inv_id}", response_model=InvitationOut, summary="Открыть приглашение",
            description="Кандидат открывает приглашение — статус sent → viewed.", responses=responses(404))
async def open_invitation(inv_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    inv = await _own_invitation(session, inv_id, user)
    if inv.status == "sent":
        inv.status, inv.updated_at = "viewed", utcnow()
        await session.commit()
    return await repo.invitation_out(session, inv, for_employer=False)


async def _decide(session: AsyncSession, inv_id: int, user: User, status: str):
    inv = await _own_invitation(session, inv_id, user)
    if inv.status in ("accepted", "declined"):
        raise ApiError(409, "already_decided", "По приглашению уже принято решение")
    inv.status, inv.updated_at = status, utcnow()
    await session.commit()
    return await repo.invitation_out(session, inv, for_employer=False)


@router.post("/invitations/{inv_id}/accept", response_model=InvitationOut, summary="Принять приглашение",
             description="После принятия работодатель видит контакты кандидата.", responses=responses(404, 409))
async def accept(inv_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    return await _decide(session, inv_id, user, "accepted")


@router.post("/invitations/{inv_id}/decline", response_model=InvitationOut, summary="Отклонить приглашение",
             description="Контакты кандидата остаются скрытыми; работодатель видит статус declined.", responses=responses(404, 409))
async def decline(inv_id: int, user: User = Depends(candidate), session: AsyncSession = Depends(get_session)):
    return await _decide(session, inv_id, user, "declined")
