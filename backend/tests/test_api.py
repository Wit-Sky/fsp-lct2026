"""API: сквозной путь, кулдаун, скрытие контактов, разграничение доступа."""
import pytest

from app.db import SessionLocal
from app.models import GradeAttempt
from tests.conftest import demo, register

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _pass_test(client, h, spec, grade, correct=True):
    r = await client.post("/api/tests/start", json={"spec": spec, "claimed_grade": grade}, headers=h)
    assert r.status_code == 201, r.text
    st = r.json()
    from app.services import testing
    while not st["finished"]:
        item = st["item"]
        assert "answer" not in item
        # правильный ответ сервер не отдаёт — достаём из состояния попытки в БД
        async with SessionLocal() as s:
            a = await s.get(GradeAttempt, st["attempt_id"])
            ans = a.items["current"]["answer"]
            if not correct:
                ans = testing._wrong(a.items["current"])
        r = await client.post(f"/api/tests/{st['attempt_id']}/answer", json={"item_id": item["item_id"], "answer": ans}, headers=h)
        assert r.status_code == 200, r.text
        st = r.json()
    return st["attempt_id"]


async def test_health_and_docs(client):
    assert (await client.get("/api/health")).json() == {"status": "ok"}
    spec = (await client.get("/api/openapi.json")).json()
    assert "/api/needs/{need_id}/matches" in spec["paths"]


async def test_end_to_end(client):
    # кандидат: регистрация → профиль → тест → категория
    hc = await register(client, "e2e@example.ru")
    r = await client.put("/api/me/profile", headers=hc, json={
        "full_name": "Сквозной Тест", "spec": "backend", "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "work_format": "hybrid", "salary_expect_from": 150000, "consent_pd": True, "phone": "+7 900 111-22-33",
        "telegram": "@e2e_user", "birth_date": "1998-05-01"})
    assert r.status_code == 200 and r.json()["published"]
    attempt = await _pass_test(client, hc, "backend", "middle")
    res = (await client.get(f"/api/tests/{attempt}/result", headers=hc)).json()
    assert res["confirmed"] and res["category"]["status"] == "confirmed"
    cat = (await client.get("/api/me/category", headers=hc)).json()
    assert cat["grade"] == "middle" and cat["status"] == "confirmed"
    me = (await client.get("/api/me/profile", headers=hc)).json()

    # работодатель: потребность → категории → подборка с explain, контакты скрыты
    he = await register(client, "hr-e2e@example.ru", "employer")
    await client.put("/api/employer", headers=he, json={"name": "ООО «Тест»", "field": "ИТ"})
    r = await client.post("/api/needs", headers=he, json={
        "title": "Python middle", "spec": "backend", "grade": "middle", "salary_from": 150000, "salary_to": 250000,
        "salary_type": "gross", "work_format": "hybrid",
        "skills": [{"name": "Python", "weight": 3}, {"name": "FastAPI", "weight": 2}, {"name": "Docker", "weight": 1}]})
    assert r.status_code == 201, r.text
    need_id = r.json()["search_id"]
    cats = (await client.get(f"/api/needs/{need_id}/categories", headers=he)).json()
    assert any(c["target"] and c["total"] > 0 for c in cats)
    m = (await client.get(f"/api/needs/{need_id}/matches", headers=he)).json()
    mine = next(x for x in m["items"] if x["candidate_id"] == me["user_id"])
    assert mine["explain"] and mine["candidate"]["contacts_hidden"] and mine["candidate"]["phone"] is None
    scores = [x["score"] for x in m["items"]]
    assert scores == sorted(scores, reverse=True)
    m2 = (await client.get(f"/api/needs/{need_id}/matches?grade_adj=true&skills=Docker", headers=he)).json()
    assert m2["filters"]["skills"] == ["Docker"]
    assert (await client.get(f"/api/searches/{need_id}", headers=he)).json()["title"] == "Python middle"

    # приглашение без зарплаты — 422; с зарплатой — 201
    bad = await client.post("/api/invitations", headers=he, json={"candidate_id": me["user_id"], "message": "Привет",
                                                                  "contact_method": "Telegram"})
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"
    r = await client.post("/api/invitations", headers=he, json={
        "candidate_id": me["user_id"], "need_id": need_id, "message": "Приглашаем на собеседование",
        "salary_from": 200000, "salary_to": 250000, "salary_type": "net", "contact_method": "Telegram @hr_test"})
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]
    card = (await client.get(f"/api/candidates/{me['user_id']}", headers=he)).json()
    assert card["contacts_hidden"] and card["email"] is None and card["invitation_status"] == "sent"

    # кандидат открывает и принимает → контакты видны
    lst = (await client.get("/api/me/invitations", headers=hc)).json()
    assert lst[0]["salary_from"] == 200000 and lst[0]["company"] == "ООО «Тест»"
    assert (await client.get(f"/api/invitations/{inv_id}", headers=hc)).json()["status"] == "viewed"
    assert (await client.post(f"/api/invitations/{inv_id}/accept", headers=hc)).json()["status"] == "accepted"
    card = (await client.get(f"/api/candidates/{me['user_id']}", headers=he)).json()
    assert not card["contacts_hidden"] and card["phone"] == "+7 900 111-22-33" and card["email"] == "e2e@example.ru"
    invs = (await client.get("/api/employer/invitations", headers=he)).json()
    assert invs[0]["candidate_contacts"]["telegram"] == "@e2e_user"


async def test_cooldown(client):
    h = await register(client, "cool@example.ru")
    await client.put("/api/me/profile", headers=h, json={"full_name": "Кулдаун", "consent_pd": True})
    await _pass_test(client, h, "frontend", "senior", correct=False)          # провал senior
    r = await client.post("/api/tests/start", json={"spec": "frontend", "claimed_grade": "senior"}, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "cooldown" and r.json()["next_attempt_at"]
    r = await client.post("/api/tests/start", json={"spec": "frontend", "claimed_grade": "middle"}, headers=h)
    assert r.status_code == 201                                                 # грейд ниже — сразу


async def test_candidate_cannot_read_others_invitations(client):
    he = await demo(client, "employer")
    ha = await register(client, "alice@example.ru")
    hb = await register(client, "bob@example.ru")
    for h, name in ((ha, "Алиса"), (hb, "Боб")):
        await client.put("/api/me/profile", headers=h, json={"full_name": name, "consent_pd": True})
    ida = (await client.get("/api/me/profile", headers=ha)).json()["user_id"]
    r = await client.post("/api/invitations", headers=he, json={
        "candidate_id": ida, "message": "Оффер", "salary_from": 100000, "salary_to": 150000, "salary_type": "gross",
        "contact_method": "email"})
    inv = r.json()["id"]
    assert (await client.get(f"/api/invitations/{inv}", headers=hb)).status_code == 404
    assert (await client.post(f"/api/invitations/{inv}/accept", headers=hb)).status_code == 404
    assert (await client.get("/api/me/invitations", headers=hb)).json() == []
    assert (await client.get("/api/needs/1/matches", headers=ha)).status_code == 403   # роль


async def test_seeded_candidate_without_fsp_in_matches(client):
    he = await demo(client, "employer")
    needs = (await client.get("/api/employer/needs", headers=he)).json()
    m = (await client.get(f"/api/needs/{needs[-1]['id']}/matches?limit=300", headers=he)).json()
    no_fsp = [x for x in m["items"] if not x["candidate"]["has_fsp"]]
    assert no_fsp, "в подборке должны быть кандидаты без истории ФСП"
    assert all(any("Нет истории ФСП" in e["text"] for e in x["explain"]) for x in no_fsp)


async def test_vacancy_apply_reveals_contacts(client):
    hc = await register(client, "apply@example.ru")
    await client.put("/api/me/profile", headers=hc, json={"full_name": "Откликнувшийся", "consent_pd": True, "phone": "+7 900 555-66-77"})
    vacs = (await client.get("/api/vacancies", headers=hc)).json()
    demo_vac = next(v for v in vacs if v["company"] == "ООО «Демо Работодатель»")
    r = await client.post(f"/api/vacancies/{demo_vac['id']}/apply", headers=hc, json={"message": "Хочу к вам"})
    assert r.status_code == 201
    assert (await client.post(f"/api/vacancies/{demo_vac['id']}/apply", headers=hc)).status_code == 409
    he = await demo(client, "employer")
    apps = (await client.get(f"/api/needs/{demo_vac['id']}/applications", headers=he)).json()
    assert apps[0]["candidate"]["phone"] == "+7 900 555-66-77"
    assert (await client.get("/api/me/applications", headers=hc)).json()[0]["status"] == "viewed"


async def test_fsp_mock_flow(client):
    hc = await demo(client, "candidate")
    token = hc["Authorization"].split()[1]
    r = await client.get(f"/api/auth/fsp/authorize?token={token}", follow_redirects=False)
    assert r.status_code == 302
    page = await client.get(r.headers["location"])
    assert "ФСП ID" in page.text
    import re
    link = re.search(r"href='(/api/auth/fsp/callback\?[^']+)'", page.text)
    assert link, "нет свободных записей реестра"
    r = await client.get(link.group(1).replace("&amp;", "&"), follow_redirects=False)
    assert r.status_code == 302 and "fsp=linked" in r.headers["location"]
    res = (await client.get("/api/me/results", headers=hc)).json()
    assert res["fsp_linked"]


async def test_profile_pdf_and_minor(client):
    hc = await register(client, "young@example.ru")
    r = await client.put("/api/me/profile", headers=hc, json={"full_name": "Юный Кандидат", "birth_date": "2010-01-01", "consent_pd": True})
    assert r.json()["minor"] and not r.json()["published"]
    r = await client.put("/api/me/profile", headers=hc, json={"parent_consent": True})
    assert r.json()["published"]
    pdf = await client.get("/api/me/profile.pdf", headers=hc)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"


async def test_resume_pdf_parse_and_roles_in_profile(client):
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import app.pdf  # noqa: F401 — регистрирует кириллический шрифт DejaVuSans
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("DejaVuSans", 11)
    for i, line in enumerate(["Смирнова Анна Олеговна", "anna@example.ru, +7 900 123-45-67",
                              "Frontend-разработчик, опыт 2 года. Наставник стажёров.",
                              "Стек: React, TypeScript, CSS. Коммуникабельность, самостоятельность."]):
        c.drawString(60, 780 - 18 * i, line)
    c.save()
    hc = await register(client, "resume@example.ru")
    r = await client.post("/api/me/resume/parse", headers=hc, files={"file": ("cv.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["full_name"] == "Смирнова Анна Олеговна" and d["spec"] == "frontend" and d["experience_years"] == 2
    assert "Ментор" in d["roles"] and {"Коммуникация", "Самостоятельность"} <= set(d["soft_skills"])
    bad = await client.post("/api/me/resume/parse", headers=hc, files={"file": ("cv.pdf", b"not a pdf", "application/pdf")})
    assert bad.status_code == 422
    r = await client.put("/api/me/profile", headers=hc, json={"roles": d["roles"], "soft_skills": d["soft_skills"]})
    assert r.json()["roles"] == d["roles"] and r.json()["soft_skills"] == d["soft_skills"]


async def test_regular_tasks_flow(client):
    he = await register(client, "hr-tasks@example.ru", "employer")
    await client.put("/api/employer", headers=he, json={"name": "ООО «Задачи»"})
    r = await client.post("/api/tasks", headers=he, json={"title": "Кэш для каталога", "spec": "backend", "grade": "junior",
                                                          "kind": "approach", "text": "Каталог товаров читается в 100 раз чаще, чем меняется. Как ускорить?"})
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    assert (await client.post("/api/tasks", headers=he, json={"title": "x", "spec": "backend", "text": "коротко"})).status_code == 422

    # кандидат без специализации заданий не получает; с категорией backend/junior — получает
    hc = await register(client, "tasks-cand@example.ru")
    mine = (await client.get("/api/me/tasks", headers=hc)).json()
    assert mine["offered"] == [] and mine["hint"]
    await client.put("/api/me/profile", headers=hc, json={"full_name": "Решатель Задач", "spec": "backend", "consent_pd": True,
                                                         "visible_fields": {"full_name": True}})
    await _pass_test(client, hc, "backend", "junior")
    mine = (await client.get("/api/me/tasks", headers=hc)).json()
    assert task_id in [t["id"] for t in mine["offered"]]
    r = await client.post(f"/api/tasks/{task_id}/answer", headers=hc, json={"answer": "Кэш в Redis с инвалидацией по событию изменения."})
    assert r.status_code == 201, r.text
    answer_id = r.json()["id"]
    assert (await client.post(f"/api/tasks/{task_id}/answer", headers=hc, json={"answer": "Повторный ответ на задание."})).status_code == 409
    assert task_id not in [t["id"] for t in (await client.get("/api/me/tasks", headers=hc)).json()["offered"]]

    # работодатель видит ответ без контактов и оценивает; чужой работодатель — нет
    ans = (await client.get(f"/api/tasks/{task_id}/answers", headers=he)).json()
    assert ans[0]["candidate_name"] == "Решатель Задач" and ans[0]["candidate_grade"] == "junior" and "email" not in ans[0]
    other = await demo(client, "employer")
    assert (await client.get(f"/api/tasks/{task_id}/answers", headers=other)).status_code == 404
    assert (await client.post(f"/api/task-answers/{answer_id}/review", headers=other, json={"rating": 3})).status_code == 404
    r = await client.post(f"/api/task-answers/{answer_id}/review", headers=he, json={"rating": 2, "feedback": "Хорошо, учтите TTL"})
    assert r.json()["rating"] == 2
    mine = (await client.get("/api/me/tasks", headers=hc)).json()
    assert mine["answered"][0]["rating"] == 2 and mine["answered"][0]["feedback"] == "Хорошо, учтите TTL"
    assert (await client.get("/api/employer/tasks", headers=he)).json()[0]["answers"] == 1

    # снятое задание больше не предлагается
    assert (await client.post(f"/api/tasks/{task_id}/close", headers=he)).json()["active"] is False
    hc2 = await register(client, "tasks-cand2@example.ru")
    await client.put("/api/me/profile", headers=hc2, json={"spec": "backend", "consent_pd": True})
    assert task_id not in [t["id"] for t in (await client.get("/api/me/tasks", headers=hc2)).json()["offered"]]


async def test_demo_tasks_seeded(client):
    hc = await demo(client, "candidate")
    await client.put("/api/me/profile", headers=hc, json={"spec": "frontend"})
    offered = (await client.get("/api/me/tasks", headers=hc)).json()["offered"]
    assert any(t["company"] == "ООО «Демо Работодатель»" and t["spec"] == "frontend" for t in offered)
