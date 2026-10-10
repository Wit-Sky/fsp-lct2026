"""Сид при пустой БД: data/*.json (CONTRACT 8.2) + демо-аккаунты для жюри.

Для каждого кандидата прогоняется настоящий тест (testing.simulate_attempt с θ_true из данных), поэтому
θ и категории в базе получены тем же механизмом, что и у живых пользователей. θ_true в БД не попадает.
id кандидатов совпадают с candidates.json — на них ссылаются pairs_labeled*.json.
Запуск: python -m app.seed
"""
import asyncio
import hashlib
import json
import logging
from datetime import date, timedelta

from sqlalchemy import func, select, text

from app import config
from app.auth import hash_password
from app.db import SessionLocal, engine, utcnow
from app.models import (CandidateProfile, Category, Employer, ExternalIdentity, GradeAttempt, Need, User,
                        VerifiedResult)
from app.services import testing

log = logging.getLogger("seed")
EMPLOYER_USER_BASE = 1000          # id пользователей-работодателей: 1001, 1002, …
DEMO_CANDIDATE_ID, DEMO_EMPLOYER_USER_ID, DEMO_EMPLOYER_ID = 900, 901, 900


def _load(name: str) -> list:
    path = config.DATA_DIR / name
    if not path.exists():
        log.warning("нет %s — пропускаю", path)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _days_ago(cid: int) -> int:
    """Детерминированная «давность теста» 1–420 дней — чтобы фактор свежести различался."""
    return 1 + int(hashlib.sha256(f"tested:{cid}".encode()).hexdigest()[:8], 16) % 420


def _seed_result(cid: int, spec: str, claimed: str, theta_true: float) -> dict:
    sim = testing.simulate_attempt(cid, spec, claimed, theta_true, 1, rng_seed=cid)
    state = {"spec": spec, "claimed_grade": claimed, "n_items": len(sim["items"]),
             "responses": [dict(i) for i in sim["items"]], "current": None, "seeded": True}
    res = testing.finish(state)
    state["result"] = res
    return state


async def seed() -> bool:
    async with SessionLocal() as s:
        if (await s.execute(select(func.count()).select_from(User))).scalar_one() > 0:
            log.info("БД не пуста — сид пропущен")
            return False
        now = utcnow()
        pwd = hash_password("demo")

        # работодатели и потребности
        for e in _load("employers.json"):
            uid = EMPLOYER_USER_BASE + e["id"]
            s.add(User(id=uid, email=e["owner_email"].lower(), password_hash=pwd, role="employer", email_verified=True))
            s.add(Employer(id=e["id"], owner_id=uid, name=e["name"], inn=e.get("inn"), field=e.get("field"),
                           description=e.get("description"), contacts=e.get("contacts")))
        await s.flush()
        for n in _load("needs.json"):
            s.add(Need(id=n["id"], employer_id=n["employer_id"], title=n["title"], spec=n["spec"], grade=n["grade"],
                       skills=n["skills"], description=n.get("description"), salary_from=n["salary_from"],
                       salary_to=n["salary_to"], salary_type=n["salary_type"], work_format=n.get("work_format"),
                       published=bool(n.get("published"))))

        # кандидаты: профиль, внешняя учётная запись, подтверждённые результаты, настоящая попытка теста и категория
        for c in _load("candidates.json"):
            cid = c["id"]
            s.add(User(id=cid, email=c["email"].lower(), password_hash=pwd, role="candidate", email_verified=True))
            s.add(CandidateProfile(
                user_id=cid, full_name=c["full_name"], birth_date=date.fromisoformat(c["birth_date"]) if c.get("birth_date") else None,
                phone=c.get("phone"), telegram=c.get("telegram"), city=c.get("city"), work_format=c.get("work_format"),
                salary_expect_from=c.get("salary_expect_from"), spec=c["spec"], skills=c.get("skills", []),
                experience_years=c.get("experience_years"), about=c.get("about"), consent_pd=True,
                parent_consent=True, visible_fields={}))
            if c.get("fsp_id"):
                s.add(ExternalIdentity(user_id=cid, provider="fsp", subject=c["fsp_id"], linked_at=now,
                                       claims={"sub": c["fsp_id"], "name": c["full_name"], "email": c["email"]}))
            for r in c.get("results", []):
                s.add(VerifiedResult(user_id=cid, source=r.get("source", "fsp"), external_id=r["external_id"], event=r["event"],
                                     discipline=r["discipline"], year=int(r["year"]), place=r.get("place"), role=r["role"],
                                     team=bool(r.get("team")), imported_at=now))
            if not testing.has_bank(c["spec"]):
                continue
            tested = now - timedelta(days=_days_ago(cid))
            state = _seed_result(cid, c["spec"], c["claimed_grade"], float(c["theta_true"]))
            res = state["result"]
            s.add(GradeAttempt(user_id=cid, spec=c["spec"], claimed_grade=c["claimed_grade"], attempt_no=1,
                               started_at=tested - timedelta(minutes=4), finished_at=tested, theta=res["theta"],
                               result="confirmed" if res["confirmed"] else "failed", items=state))
            s.add(Category(user_id=cid, spec=c["spec"], grade=c["claimed_grade"],
                           status="confirmed" if res["confirmed"] else "unconfirmed", theta=res["theta"],
                           confirmed_at=tested if res["confirmed"] else None, tested_at=tested,
                           next_attempt_at=tested + timedelta(days=config.COOLDOWN_DAYS),
                           suggest_upgrade=res["suggest_upgrade"]))

        # демо-аккаунты для жюри (пароль demo; вход без пароля — POST /api/auth/demo/{role})
        s.add(User(id=DEMO_CANDIDATE_ID, email="candidate@demo.fsp", password_hash=pwd, role="candidate",
                   email_verified=True, is_demo=True))
        s.add(CandidateProfile(user_id=DEMO_CANDIDATE_ID, full_name="Демо Кандидат", city="Москва", work_format="hybrid",
                               salary_expect_from=150000, skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                               experience_years=2, about="Демо-аккаунт для жюри: без теста и без истории ФСП.",
                               phone="+7 900 000-00-00", telegram="@demo_candidate", consent_pd=True, visible_fields={}))
        s.add(User(id=DEMO_EMPLOYER_USER_ID, email="employer@demo.fsp", password_hash=pwd, role="employer",
                   email_verified=True, is_demo=True))
        await s.flush()
        s.add(Employer(id=DEMO_EMPLOYER_ID, owner_id=DEMO_EMPLOYER_USER_ID, name="ООО «Демо Работодатель»", inn="7700000000",
                       field="разработка ПО", description="Демо-компания для проверки жюри.", contacts="hr@demo.fsp"))
        await s.flush()
        s.add(Need(employer_id=DEMO_EMPLOYER_ID, title="Backend-разработчик Python (middle)", spec="backend", grade="middle",
                   skills=[{"name": "Python", "weight": 3}, {"name": "FastAPI", "weight": 2}, {"name": "PostgreSQL", "weight": 2},
                           {"name": "Docker", "weight": 1}],
                   description="Команда платформы данных: API на FastAPI, PostgreSQL, очереди.", salary_from=200000,
                   salary_to=300000, salary_type="gross", work_format="hybrid", published=True))
        s.add(Need(employer_id=DEMO_EMPLOYER_ID, title="Frontend-разработчик React (junior)", spec="frontend", grade="junior",
                   skills=[{"name": "React", "weight": 3}, {"name": "TypeScript", "weight": 2}, {"name": "CSS", "weight": 1}],
                   description="Личный кабинет клиента на React + TypeScript.", salary_from=90000, salary_to=140000,
                   salary_type="net", work_format="remote", published=False))
        await s.commit()

    if engine.dialect.name == "postgresql":       # после явных id — сдвинуть последовательности
        async with engine.begin() as conn:
            for t in ("users", "employers", "needs", "external_identities", "verified_results", "grade_attempts",
                      "categories", "invitations", "applications"):
                await conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                                        f"COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false)"))
    log.info("сид загружен")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if config.SEED_ON_START:
        asyncio.run(seed())
