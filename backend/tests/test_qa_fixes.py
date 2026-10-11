"""Регрессии отчёта Стаси: полный total, демосброс, сохранение шага и безопасный вход ФСП."""
import asyncio
import html
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import select, update

from app import config, fsp_oidc
from app.db import SessionLocal, utcnow
from app.main import app
from app.models import (Application, Category, ExternalIdentity, FspAuthorization, GradeAttempt,
                        Invitation, Need, Task, TaskAnswer, VerifiedResult)
from app.routers.auth import link_fsp
from app.services.fsp_link import COOKIE_NAME, COOKIE_PATH, digest
from tests.conftest import demo, register

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def start(client, headers):
    response = await client.post("/api/auth/fsp/start", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["authorize_url"]


async def login_page(client, headers):
    url = await start(client, headers)
    response = await client.get(url, follow_redirects=False)
    assert response.status_code == 302, response.text
    page = await client.get(response.headers["location"])
    assert page.status_code == 200, page.text
    callback = re.search(r"href='(/api/auth/fsp/callback\?[^']+)'", page.text)
    assert callback, "В реестре нет свободного ФСП ID"
    return html.unescape(callback.group(1))


async def test_matches_count_before_limit_and_after_filters(client):
    he = await register(client, "qa-total@example.ru", "employer")
    n = await client.post("/api/needs", headers=he, json={
        "title": "Проверка полного счётчика", "spec": "backend", "grade": "middle", "skills": [],
        "salary_from": 100000, "salary_to": 200000, "salary_type": "gross"})
    assert n.status_code == 201, n.text
    path = f"/api/needs/{n.json()['id']}/matches?grade_adj=true"
    limited = (await client.get(path, headers=he)).json()
    full = (await client.get(path + "&limit=300", headers=he)).json()
    assert limited["total"] == full["total"] == len(full["items"])
    assert limited["total"] > 50 and len(limited["items"]) == 50
    assert limited["items"] == full["items"][:50]
    only_fsp = (await client.get(path + "&fsp_only=true", headers=he)).json()
    expected = sum(x["candidate"]["has_fsp"] for x in full["items"])
    assert only_fsp["total"] == expected < full["total"]
    skill = (await client.get(path + "&skills=Docker&limit=1", headers=he)).json()
    assert skill["total"] == sum("Docker" in x["candidate"]["skills"] for x in full["items"])
    assert len(skill["items"]) <= 1


async def test_fsp_skip_persists_between_clients_and_is_user_scoped(client):
    hc = await register(client, "qa-skip@example.ru")
    other = await register(client, "qa-skip-other@example.ru")
    assert not (await client.get("/api/me/profile", headers=hc)).json()["fsp_skipped"]
    p = await client.put("/api/me/profile", headers=hc, json={"fsp_skipped": True})
    assert p.status_code == 200 and p.json()["fsp_skipped"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as fresh:
        assert (await fresh.get("/api/me/profile", headers=hc)).json()["fsp_skipped"]
    assert not (await client.get("/api/me/profile", headers=other)).json()["fsp_skipped"]
    assert (await client.put("/api/me/profile", headers=hc, json={"fsp_skipped": None})).status_code == 422
    assert (await client.put("/api/me/profile", headers=hc, json={"full_name": "Новый профиль"})).json()["fsp_skipped"]


async def test_fsp_start_requires_candidate_and_does_not_expose_session_token(client):
    assert (await client.post("/api/auth/fsp/start")).status_code == 401
    he = await demo(client, "employer")
    assert (await client.post("/api/auth/fsp/start", headers=he)).status_code == 403
    hc = await register(client, "qa-code@example.ru")
    r = await client.post("/api/auth/fsp/start", headers=hc)
    assert r.status_code == 200
    data = r.json()
    assert data["expires_in"] == 60
    assert hc["Authorization"].split()[1] not in str(data)
    assert "token=" not in data["authorize_url"]
    assert r.headers["cache-control"] == "no-store" and r.headers["referrer-policy"] == "no-referrer"
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=lax" in r.headers["set-cookie"]
    code = parse_qs(urlsplit(data["authorize_url"]).query)["code"][0]
    assert (await client.get("/api/me/profile", headers={"Authorization": f"Bearer {code}"})).status_code == 401
    # Старый браузерный вход с bearer в адресе больше не работает.
    assert (await client.get("/api/auth/fsp/authorize", params={"token": hc["Authorization"].split()[1]})).status_code == 422
    spec = (await client.get("/api/openapi.json")).json()
    params = spec["paths"]["/api/auth/fsp/authorize"]["get"]["parameters"]
    assert all(p["name"] != "token" for p in params)


async def test_fsp_cookie_is_secure_on_https(client, monkeypatch):
    hc = await register(client, "qa-secure-cookie@example.ru")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://stand.example.ru")
    r = await client.post("/api/auth/fsp/start", headers=hc)
    assert r.status_code == 200 and "Secure" in r.headers["set-cookie"]


async def test_fsp_authorize_bound_to_browser_and_single_use_atomically(client):
    hc = await register(client, "qa-once@example.ru")
    url = await start(client, hc)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as stranger:
        assert (await stranger.get(url)).status_code == 400
        stranger.cookies.set(COOKIE_NAME, "wrong-browser", path=COOKIE_PATH)
        assert (await stranger.get(url)).status_code == 400
    responses = await asyncio.gather(client.get(url), client.get(url))
    assert sorted(r.status_code for r in responses) == [302, 400]
    redirected = next(r for r in responses if r.status_code == 302)
    assert "token=" not in redirected.headers["location"]
    state = parse_qs(urlsplit(redirected.headers["location"]).query)["state"][0]
    assert "." not in state  # opaque state, не JWT пользователя


async def test_fsp_authorize_rejects_expired_code(client):
    hc = await register(client, "qa-expired-code@example.ru")
    url = await start(client, hc)
    code = parse_qs(urlsplit(url).query)["code"][0]
    async with SessionLocal() as s:
        await s.execute(update(FspAuthorization).where(FspAuthorization.code_hash == digest(code))
                        .values(expires_at=utcnow() - timedelta(seconds=1)))
        await s.commit()
    r = await client.get(url)
    assert r.status_code == 400 and r.json()["code"] == "invalid_code"


async def test_fsp_callback_is_browser_bound_and_cannot_replay(client):
    hc = await register(client, "qa-callback@example.ru")
    await client.put("/api/me/profile", headers=hc, json={"fsp_skipped": True})
    url = await login_page(client, hc)
    binding = client.cookies.get(COOKIE_NAME)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as stranger:
        assert (await stranger.get(url)).status_code == 400
    responses = await asyncio.gather(client.get(url), client.get(url))
    assert sorted(r.status_code for r in responses) == [302, 400]
    assert (await client.get("/api/me/results", headers=hc)).json()["fsp_linked"]
    assert not (await client.get("/api/me/profile", headers=hc)).json()["fsp_skipped"]
    client.cookies.set(COOKIE_NAME, binding, domain="test.local", path=COOKIE_PATH)
    assert (await client.get(url)).status_code == 400
    # Явная отвязка очищает результаты и решение шага.
    assert (await client.delete("/api/me/fsp", headers=hc)).status_code == 204
    assert not (await client.get("/api/me/results", headers=hc)).json()["fsp_linked"]


async def test_fsp_callback_rejects_expired_state(client):
    hc = await register(client, "qa-expired-state@example.ru")
    url = await login_page(client, hc)
    state = parse_qs(urlsplit(url).query)["state"][0]
    async with SessionLocal() as s:
        await s.execute(update(FspAuthorization).where(FspAuthorization.state_hash == digest(state))
                        .values(state_expires_at=utcnow() - timedelta(seconds=1)))
        await s.commit()
    r = await client.get(url)
    assert r.status_code == 400 and r.json()["code"] == "invalid_state"


async def test_demo_reset_frees_fsp_and_only_resets_demo_candidate(client):
    hc = await demo(client, "candidate")
    normal = await register(client, "qa-reset-unaffected@example.ru")
    demo_id = (await client.get("/api/me/profile", headers=hc)).json()["user_id"]
    normal_id = (await client.get("/api/me/profile", headers=normal)).json()["user_id"]
    await client.put("/api/me/profile", headers=hc, json={"full_name": "", "fsp_skipped": True})
    callback = await login_page(client, hc)
    assert (await client.get(callback)).status_code == 302
    fsp_id = (await client.get("/api/me/profile", headers=hc)).json()["fsp_id"]
    await start(client, hc)
    attempt = await client.post("/api/tests/start", headers=hc, json={"spec": "backend", "claimed_grade": "junior"})
    assert attempt.status_code == 201, attempt.text
    async with SessionLocal() as s:
        need = (await s.execute(select(Need).where(Need.published.is_(True)))).scalars().first()
        task = (await s.execute(select(Task))).scalars().first()
        linked = set((await s.execute(select(ExternalIdentity.subject))).scalars())
        other_fsp = next(e["fsp_id"] for e in fsp_oidc.registry() if e["fsp_id"] not in linked)
        await link_fsp(s, normal_id, {"sub": other_fsp})
        s.add(GradeAttempt(user_id=normal_id, spec="backend", claimed_grade="middle", items={}))
        s.add(Category(user_id=demo_id, spec="backend", grade="junior", status="unconfirmed"))
        s.add(Invitation(candidate_id=demo_id, employer_id=need.employer_id, need_id=need.id, message="Демо",
                         salary_from=100000, salary_to=200000, salary_type="gross", contact_method="email"))
        s.add(Application(candidate_id=demo_id, need_id=need.id))
        s.add(TaskAnswer(candidate_id=demo_id, task_id=task.id, answer="Демо"))
        await s.commit()
    hc = await demo(client, "candidate")
    p = (await client.get("/api/me/profile", headers=hc)).json()
    assert p["full_name"] == "Демо Кандидат" and not p["fsp_linked"] and not p["fsp_skipped"]
    assert (await client.get("/api/me/category", headers=hc)).json()["attempts"] == []
    async with SessionLocal() as s:
        for model, key in ((FspAuthorization, FspAuthorization.user_id), (ExternalIdentity, ExternalIdentity.user_id),
                           (VerifiedResult, VerifiedResult.user_id), (Category, Category.user_id),
                           (Invitation, Invitation.candidate_id), (Application, Application.candidate_id),
                           (TaskAnswer, TaskAnswer.candidate_id)):
            assert not (await s.execute(select(model).where(key == demo_id))).scalars().all()
        assert (await s.execute(select(GradeAttempt).where(GradeAttempt.user_id == normal_id))).scalars().all()
        assert (await s.execute(select(ExternalIdentity).where(ExternalIdentity.user_id == normal_id))).scalars().all()
        assert not (await s.execute(select(ExternalIdentity).where(ExternalIdentity.subject == fsp_id))).scalars().all()
    # Освободившийся участник снова доступен следующему посетителю демо.
    callback = await login_page(client, hc)
    r = await client.get(callback)
    assert r.status_code == 302
    await demo(client, "candidate")


async def test_demo_entry_disabled_outside_demo_mode(client, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", False)
    assert (await client.post("/api/auth/demo/candidate")).status_code == 404


async def test_abandoned_expired_attempt_does_not_confirm_junior(client):
    hc = await register(client, "qa-empty-attempt@example.ru")
    await client.put("/api/me/profile", headers=hc, json={"full_name": "Пустая попытка", "consent_pd": True})
    attempt = await client.post("/api/tests/start", headers=hc, json={"spec": "backend", "claimed_grade": "junior"})
    assert attempt.status_code == 201, attempt.text
    attempt_id = attempt.json()["attempt_id"]
    async with SessionLocal() as s:
        await s.execute(update(GradeAttempt).where(GradeAttempt.id == attempt_id)
                        .values(started_at=utcnow() - config.TEST_TIME_LIMIT - timedelta(minutes=1)))
        await s.commit()
    res = (await client.get(f"/api/tests/{attempt_id}/result", headers=hc)).json()
    assert res["correct"] == 0 and res["total"] == 10 and res["unanswered"] == 10
    assert not res["confirmed"] and res["theta"] < -0.5
    assert res["category"]["status"] == "unconfirmed"


async def test_not_found_gender_and_finished_state_hides_item_difficulty(client):
    he = await register(client, "qa-404@example.ru", "employer")
    r = await client.get("/api/needs/999999/matches", headers=he)
    assert r.status_code == 404 and r.json()["detail"] == "Потребность не найдена"
    hc = await register(client, "qa-state-b@example.ru")
    assert (await client.get("/api/tests/999999", headers=hc)).json()["detail"] == "Попытка не найдена"
    await client.put("/api/me/profile", headers=hc, json={"full_name": "Без b", "consent_pd": True})
    st = (await client.post("/api/tests/start", headers=hc, json={"spec": "backend", "claimed_grade": "junior"})).json()
    async with SessionLocal() as s:
        await s.execute(update(GradeAttempt).where(GradeAttempt.id == st["attempt_id"])
                        .values(started_at=utcnow() - config.TEST_TIME_LIMIT - timedelta(minutes=1)))
        await s.commit()
    state = (await client.get(f"/api/tests/{st['attempt_id']}", headers=hc)).json()
    assert state["finished"] and state["result"]["total"] == 10 and "items" not in state["result"]
