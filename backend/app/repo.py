"""Загрузка данных из БД в словари для чистых модулей (testing / profile / matching) и сборка ответов."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import aware
from app.models import (Application, CandidateProfile, Category, Employer, ExternalIdentity, Invitation, Need,
                        User, VerifiedResult)
from app.services import matching, profile as profile_svc


def result_dict(r: VerifiedResult) -> dict:
    return {"id": r.id, "source": r.source, "external_id": r.external_id, "event": r.event, "discipline": r.discipline,
            "year": r.year, "place": r.place, "role": r.role, "team": r.team}


async def load_candidates(session: AsyncSession, spec: str | None = None, ids: list[int] | None = None,
                          only_published: bool = True, with_category_only: bool = True) -> list[dict]:
    """Кандидаты как словари формата candidates.json + {grade, status, theta, tested_at, fsp_score, fsp_explain}.

    spec задан — категория именно по этой специализации; иначе — по специализации профиля."""
    q = select(User, CandidateProfile).join(CandidateProfile, CandidateProfile.user_id == User.id).where(User.role == "candidate")
    if ids is not None:
        q = q.where(User.id.in_(ids))
    rows = (await session.execute(q)).all()
    if not rows:
        return []
    uids = [u.id for u, _ in rows]
    cats: dict[int, list[Category]] = {}
    for c in (await session.execute(select(Category).where(Category.user_id.in_(uids)))).scalars():
        cats.setdefault(c.user_id, []).append(c)
    res: dict[int, list[dict]] = {}
    for r in (await session.execute(select(VerifiedResult).where(VerifiedResult.user_id.in_(uids)))).scalars():
        res.setdefault(r.user_id, []).append(result_dict(r))
    fsp_ids = {e.user_id: e.subject for e in (await session.execute(
        select(ExternalIdentity).where(ExternalIdentity.user_id.in_(uids), ExternalIdentity.provider == "fsp"))).scalars()}

    out = []
    today = date.today()
    for u, p in rows:
        pd = {"consent_pd": p.consent_pd, "parent_consent": p.parent_consent, "birth_date": p.birth_date}
        if only_published and not profile_svc.publishable(pd, today):
            continue
        ucats = cats.get(u.id, [])
        cat = next((c for c in ucats if c.spec == spec), None) if spec else \
            (next((c for c in ucats if c.spec == p.spec), None) or (ucats[0] if ucats else None))
        if with_category_only and cat is None:
            continue
        cspec = cat.spec if cat else (spec or p.spec)
        results = res.get(u.id, [])
        fs, fx = profile_svc.fsp_score(results, cspec or "backend")
        out.append({
            "id": u.id, "email": u.email, "full_name": p.full_name, "birth_date": p.birth_date, "phone": p.phone,
            "telegram": p.telegram, "city": p.city, "work_format": p.work_format,
            "salary_expect_from": p.salary_expect_from, "experience_years": p.experience_years,
            "spec": cspec, "claimed_grade": cat.grade if cat else None, "skills": list(p.skills or []), "about": p.about,
            "roles": list(p.roles or []), "soft_skills": list(p.soft_skills or []),
            "fsp_id": fsp_ids.get(u.id), "results": results, "visible_fields": dict(p.visible_fields or {}),
            "grade": cat.grade if cat else None, "status": cat.status if cat else "none",
            "theta": cat.theta if cat else None, "tested_at": aware(cat.tested_at) if cat else None,
            "minor": profile_svc.is_minor(p.birth_date, today), "fsp_score": fs, "fsp_explain": fx,
        })
    return out


def with_percentiles(cands: list[dict], population: list[dict] | None = None) -> list[dict]:
    pops: dict[tuple, list[float]] = {}
    for c in population if population is not None else cands:
        if c.get("theta") is not None and c.get("grade"):
            pops.setdefault((c["spec"], c["grade"]), []).append(c["theta"])
    for c in cands:
        c["theta_pct"] = matching.percentile(c.get("theta"), pops.get((c.get("spec"), c.get("grade")), [])) \
            if c.get("theta") is not None else None
    return cands


async def visible_contacts(session: AsyncSession, employer_id: int) -> set[int]:
    """Кандидаты, чьи контакты видит работодатель: принял его приглашение или сам откликнулся на его вакансию."""
    acc = (await session.execute(select(Invitation.candidate_id).where(
        Invitation.employer_id == employer_id, Invitation.status == "accepted"))).scalars().all()
    app = (await session.execute(select(Application.candidate_id).join(Need, Need.id == Application.need_id).where(
        Need.employer_id == employer_id))).scalars().all()
    return set(acc) | set(app)


async def invitation_statuses(session: AsyncSession, employer_id: int) -> dict[int, str]:
    rows = (await session.execute(select(Invitation.candidate_id, Invitation.status).where(
        Invitation.employer_id == employer_id).order_by(Invitation.created_at))).all()
    return {cid: st for cid, st in rows}


def card(c: dict, contacts_visible: bool, invitation_status: str | None = None) -> dict:
    base = {k: c.get(k) for k in ("id", "full_name", "city", "birth_date", "about", "experience_years", "work_format",
                                  "salary_expect_from", "spec", "skills", "roles", "soft_skills", "grade", "status", "theta", "tested_at",
                                  "results", "email", "phone", "telegram", "visible_fields", "minor")}
    base["percentile"] = c.get("theta_pct")
    base["has_fsp"] = bool(c.get("results"))
    out = profile_svc.employer_view(base, contacts_visible)
    out["birth_date"] = None              # дату рождения не показываем, достаточно пометки minor
    out["invitation_status"] = invitation_status
    return out


async def invitation_out(session: AsyncSession, inv: Invitation, for_employer: bool) -> dict:
    emp = await session.get(Employer, inv.employer_id)
    need = await session.get(Need, inv.need_id) if inv.need_id else None
    prof = await session.get(CandidateProfile, inv.candidate_id)
    out = {"id": inv.id, "need_id": inv.need_id, "need_title": need.title if need else None,
           "employer_id": inv.employer_id, "company": emp.name if emp else "", "candidate_id": inv.candidate_id,
           "candidate_name": prof.full_name if (prof and for_employer) else None,
           "message": inv.message, "salary_from": inv.salary_from, "salary_to": inv.salary_to,
           "salary_type": inv.salary_type, "contact_method": inv.contact_method, "status": inv.status,
           "created_at": aware(inv.created_at), "updated_at": aware(inv.updated_at), "candidate_contacts": None}
    if for_employer and inv.status == "accepted":
        user = await session.get(User, inv.candidate_id)
        out["candidate_contacts"] = {"email": user.email if user else None, "phone": prof.phone if prof else None,
                                     "telegram": prof.telegram if prof else None}
    return out


def need_dict(n: Need) -> dict:
    return {"id": n.id, "employer_id": n.employer_id, "title": n.title, "spec": n.spec, "grade": n.grade,
            "skills": list(n.skills or []), "description": n.description, "salary_from": n.salary_from,
            "salary_to": n.salary_to, "salary_type": n.salary_type, "work_format": n.work_format,
            "published": n.published, "created_at": aware(n.created_at)}
