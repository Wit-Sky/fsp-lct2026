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
- ~~Docker не запущен~~ — исправлено, см. ниже.
- ~~`docs/bas_samples.md`~~ — готово, на вычитку Евгению.

## 11.10, ~02:30 МСК — Postgres, docs/backend.md
- Образ собран и запущен на `postgres:16-alpine`: миграция, сид, `/api/health`, `/api/docs` — ок.
- Найдено и исправлено два бага, которые SQLite не ловил: сид вставлял работодателей раньше их пользователей
  (FK), последовательности id не сдвигались до вставок с автоматическим id. В SQLite-тестах теперь включены FK.
- pytest: 17 зелёных и на SQLite, и на Postgres (`TEST_DATABASE_URL=postgresql+asyncpg://…`).
- `docs/backend.md` для Антона: слои, модули, схема БД, банк и утечка, формула, переменные окружения, pip freeze.
- Антону: `validation/results.md` в main собран на `_stub.py`. На настоящем ядре (нужны зависимости бэкенда
  + matplotlib) цифры лучше: грейд точно 64,0 %, решение о подтверждении верно 80,3 %, утечка: средний прирост θ 0,26
  против 2,82 у единого теста. Перезапустите `python -X utf8 validation/run_all.py` из venv бэкенда.
