"""Перепроверка перед стоп-кодом: вход и роли, изоляция компаний, скрытие контактов и приватность, повторные действия."""
import pytest

from tests.conftest import register

pytestmark = pytest.mark.asyncio(loop_scope="session")

NEED = {"title": "Проверка прав", "spec": "backend", "grade": "middle", "skills": [{"name": "Python", "weight": 1}],
        "salary_from": 100000, "salary_to": 200000, "salary_type": "gross"}


async def published_candidate(client, email, **profile):
    h = await register(client, email)
    r = await client.put("/api/me/profile", headers=h, json={"full_name": "Проверочный Кандидат", "consent_pd": True,
                                                             "phone": "+79990001122", "telegram": "@check_user", **profile})
    assert r.status_code == 200, r.text
    return h, (await client.get("/api/me/profile", headers=h)).json()["user_id"]


async def invite(client, he, cid, need_id=None):
    return await client.post("/api/invitations", headers=he, json={
        "candidate_id": cid, "need_id": need_id, "message": "Приглашаем", "contact_method": "email",
        "salary_from": 120000, "salary_to": 180000, "salary_type": "gross"})


async def test_verify_cannot_issue_token_for_verified_email(client):
    await register(client, "sec-victim@example.ru", "employer")
    r = await client.post("/api/auth/verify", json={"email": "sec-victim@example.ru", "code": "000000"})
    assert r.status_code == 409 and "access_token" not in r.text
    r = await client.post("/api/auth/register", json={"email": "sec-new@example.ru", "password": "secret1", "role": "candidate"})
    code = r.json()["verify_code"]
    wrong = "000000" if code != "000000" else "111111"
    assert (await client.post("/api/auth/verify", json={"email": "sec-new@example.ru", "code": wrong})).status_code == 400
    assert (await client.post("/api/auth/login", json={"email": "sec-new@example.ru", "password": "secret1"})).status_code == 403
    assert (await client.post("/api/auth/verify", json={"email": "sec-new@example.ru", "code": code})).status_code == 200
    assert (await client.post("/api/auth/login", json={"email": "sec-new@example.ru", "password": "bad-pass"})).status_code == 401
    assert (await client.post("/api/auth/login", json={"email": "SEC-NEW@example.ru", "password": "secret1"})).status_code == 200


async def test_roles_and_tokens(client):
    hc = await register(client, "sec-role-c@example.ru")
    he = await register(client, "sec-role-e@example.ru", "employer")
    assert (await client.get("/api/me/profile")).status_code == 401
    assert (await client.get("/api/me/profile", headers={"Authorization": "Bearer garbage"})).status_code == 401
    assert (await client.get("/api/employer/needs", headers=hc)).status_code == 403
    assert (await client.get("/api/candidates", headers=hc)).status_code == 403
    assert (await client.post("/api/needs", headers=hc, json=NEED)).status_code == 403
    assert (await client.get("/api/me/profile", headers=he)).status_code == 403
    assert (await client.post("/api/tests/start", headers=he, json={"spec": "backend", "claimed_grade": "junior"})).status_code == 403


async def test_employers_are_isolated(client):
    he1 = await register(client, "sec-emp1@example.ru", "employer")
    he2 = await register(client, "sec-emp2@example.ru", "employer")
    nid = (await client.post("/api/needs", headers=he1, json=NEED)).json()["id"]
    for path in (f"/api/needs/{nid}", f"/api/needs/{nid}/matches", f"/api/needs/{nid}/categories", f"/api/needs/{nid}/applications"):
        assert (await client.get(path, headers=he2)).status_code == 404, path
    assert (await client.put(f"/api/needs/{nid}", headers=he2, json=NEED)).status_code == 404
    assert (await client.post(f"/api/needs/{nid}/publish", headers=he2)).status_code == 404
    _, cid = await published_candidate(client, "sec-iso-cand@example.ru")
    assert (await invite(client, he2, cid, need_id=nid)).status_code == 404       # чужая потребность в приглашении
    assert (await invite(client, he1, cid, need_id=nid)).status_code == 201
    assert (await client.get("/api/employer/invitations", headers=he2)).json() == []
    t = (await client.post("/api/tasks", headers=he1, json={"title": "Задача", "text": "Решите задачу про индексы", "spec": "backend"})).json()
    assert (await client.get(f"/api/tasks/{t['id']}/answers", headers=he2)).status_code == 404
    assert (await client.post(f"/api/tasks/{t['id']}/close", headers=he2)).status_code == 404


async def test_contacts_hidden_until_accept_and_after_decline(client):
    he = await register(client, "sec-contacts-e@example.ru", "employer")
    hc, cid = await published_candidate(client, "sec-contacts-c@example.ru")
    hd, did = await published_candidate(client, "sec-decline-c@example.ru")
    for c in (cid, did):
        card = (await client.get(f"/api/candidates/{c}", headers=he)).json()
        assert card["contacts_hidden"] and card["email"] is card["phone"] is card["telegram"] is None
    found = [x for x in (await client.get("/api/candidates?limit=300", headers=he)).json() if x["id"] in (cid, did)]
    assert all(x["contacts_hidden"] and x["email"] is None for x in found)
    for h, c in ((hc, cid), (hd, did)):
        assert (await invite(client, he, c)).status_code == 201
    assert (await invite(client, he, cid)).status_code == 409                     # повторное, пока ждёт ответа
    inv_c = (await client.get("/api/me/invitations", headers=hc)).json()[0]["id"]
    inv_d = (await client.get("/api/me/invitations", headers=hd)).json()[0]["id"]
    assert (await client.post(f"/api/invitations/{inv_d}/accept", headers=hc)).status_code == 404   # чужое
    assert (await client.post(f"/api/invitations/{inv_d}/decline", headers=hd)).status_code == 200
    assert (await client.post(f"/api/invitations/{inv_d}/accept", headers=hd)).status_code == 409   # решение уже принято
    assert (await client.post(f"/api/invitations/{inv_c}/accept", headers=hc)).status_code == 200
    accepted = (await client.get(f"/api/candidates/{cid}", headers=he)).json()
    declined = (await client.get(f"/api/candidates/{did}", headers=he)).json()
    assert not accepted["contacts_hidden"] and accepted["email"] == "sec-contacts-c@example.ru" and accepted["phone"]
    assert declined["contacts_hidden"] and declined["email"] is None and declined["phone"] is None
    other = await register(client, "sec-contacts-other@example.ru", "employer")
    assert (await client.get(f"/api/candidates/{cid}", headers=other)).json()["contacts_hidden"]   # только этой компании


async def test_hidden_and_minor_candidates_and_privacy(client):
    he = await register(client, "sec-priv-e@example.ru", "employer")
    hn = await register(client, "sec-noconsent@example.ru")
    await client.put("/api/me/profile", headers=hn, json={"full_name": "Без Согласия"})
    nid = (await client.get("/api/me/profile", headers=hn)).json()["user_id"]
    assert (await client.get(f"/api/candidates/{nid}", headers=he)).status_code == 404
    assert (await invite(client, he, nid)).status_code == 404
    hm, mid = await published_candidate(client, "sec-minor@example.ru", birth_date="2012-01-01")
    assert (await client.get("/api/me/profile", headers=hm)).json()["published"] is False
    assert (await client.get(f"/api/candidates/{mid}", headers=he)).status_code == 404
    await client.put("/api/me/profile", headers=hm, json={"parent_consent": True})
    card = (await client.get(f"/api/candidates/{mid}", headers=he)).json()
    assert card["minor"] and card["birth_date"] is None
    hp, pid = await published_candidate(client, "sec-private@example.ru", city="Казань",
                                        visible_fields={"full_name": False, "city": False})
    card = (await client.get(f"/api/candidates/{pid}", headers=he)).json()
    assert card["full_name"] is None and card["city"] is None


async def test_attempt_isolation_and_finished_attempt(client):
    h1, _ = await published_candidate(client, "sec-att1@example.ru")
    h2, _ = await published_candidate(client, "sec-att2@example.ru")
    st = (await client.post("/api/tests/start", headers=h1, json={"spec": "backend", "claimed_grade": "junior"})).json()
    aid = st["attempt_id"]
    assert (await client.get(f"/api/tests/{aid}", headers=h2)).status_code == 404
    assert (await client.post(f"/api/tests/{aid}/answer", headers=h2, json={"item_id": st["item"]["item_id"], "answer": 0})).status_code == 404
    assert "answer" not in st["item"] and "b" not in st["item"]
    assert (await client.post(f"/api/tests/{aid}/answer", headers=h1, json={"item_id": "nope#1", "answer": 0})).status_code == 409
    assert (await client.get(f"/api/tests/{aid}/result", headers=h1)).status_code == 409             # ещё не завершён
    again = (await client.post("/api/tests/start", headers=h1, json={"spec": "backend", "claimed_grade": "junior"}))
    assert again.status_code == 201 and again.json()["attempt_id"] == aid                             # продолжение той же
    while not st["finished"]:
        r = await client.post(f"/api/tests/{aid}/answer", headers=h1, json={"item_id": st["item"]["item_id"], "answer": 0})
        assert r.status_code == 200, r.text
        st = r.json()
    assert (await client.post(f"/api/tests/{aid}/answer", headers=h1, json={"item_id": "x", "answer": 0})).status_code == 409
    res = (await client.get(f"/api/tests/{aid}/result", headers=h1)).json()
    assert res["total"] == 10 and res["unanswered"] == 0 and sum(t["total"] for t in res["topics"]) == 10


async def test_validation_on_money_and_duplicates(client):
    he = await register(client, "sec-val-e@example.ru", "employer")
    bad = {**NEED}
    bad.pop("salary_from")
    assert (await client.post("/api/needs", headers=he, json=bad)).status_code == 422
    assert (await client.post("/api/needs", headers=he, json={**NEED, "salary_from": 300000})).status_code == 422
    hc, cid = await published_candidate(client, "sec-val-c@example.ru")
    r = await client.post("/api/invitations", headers=he, json={"candidate_id": cid, "message": "x", "contact_method": "email",
                                                                 "salary_type": "gross"})
    assert r.status_code == 422
    nid = (await client.post("/api/needs", headers=he, json=NEED)).json()["id"]
    assert (await client.post(f"/api/vacancies/{nid}/apply", headers=hc)).status_code == 404       # не опубликована
    await client.post(f"/api/needs/{nid}/publish", headers=he)
    assert (await client.post(f"/api/vacancies/{nid}/apply", headers=hc)).status_code == 201
    assert (await client.post(f"/api/vacancies/{nid}/apply", headers=hc)).status_code == 409
