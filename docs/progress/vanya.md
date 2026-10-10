# Прогресс — Ваня (бэкенд)

## 11.10, 01:30 МСК — каркас + ядро в main
Готово (шаги 1–4 сразу по-настоящему, без заглушек):
- FastAPI `/api`, `/api/docs`, `/api/health`; ошибки `{detail, code}`; CORS.
- Модели раздела 5 + первая миграция alembic `0001_initial_schema` (PostgreSQL 16, async; SQLite — в тестах).
- `services/testing.py`: 66 параметрических шаблонов (backend 4×6, frontend 4×6, bas 3×6), сид варианта
  sha256(candidate:attempt:template), адаптивная сборка 10 заданий, θ по Рашу (сетка 0,01, [−3; 3]), кулдаун, симуляция.
- `services/matching.py`: формула раздела 4 + explain по-русски, keyword_baseline, category_counts.
- `services/profile.py`: import_results, fsp_score («Нет истории ФСП — оценка только по тесту»), видимость, разбор резюме.
- Все эндпоинты раздела 6 + `/api/catalog`, `/api/tests/{id}`, `/api/employer/needs`, `PUT /needs/{id}`,
  `/api/vacancies/{id}`, `/api/applications/{id}/status`, `DELETE /api/me/fsp`.
- FSP ID: OIDC-клиент (mock-страница «ФСП ID (демо)» → callback → ExternalIdentity + VerifiedResult).
- Сид: 300 кандидатов из data/*.json прогнаны настоящим тестом, 10 компаний, 30 потребностей, демо-аккаунты.
- pytest: 17 тестов зелёные (все 7 обязательных + сквозной путь).
- Dockerfile бэкенда.

Для Евгения:
- Данные для сида — том `./data:/data:ro` у сервиса backend; `DATABASE_URL=postgresql+asyncpg://...`.
- Демо-вход: `POST /api/auth/demo/candidate|employer` → `{access_token}`.
- Связать FSP ID: `window.location = "/api/auth/fsp/authorize?token=" + token` → вернёт на `FRONTEND_URL/candidate/profile?fsp=linked|conflict`.
- Ответ на задание: single — текст варианта или индекс; number — число; order — массив вариантов в нужном порядке.

Не сделано / риски:
- Docker на машине Вани ещё не запущен (нет WSL) — образ не собирался локально.
- `docs/bas_samples.md` — следующим шагом, на вычитку Евгению.
