# Прогресс — Евгений (фронтенд, сервер, сдача)

## 11.10, ~02:30 МСК — каркас фронтенда + docker-compose (ветка `frontend`)
- `docker-compose.yml`: `db` (postgres:16-alpine, healthcheck) → `backend` (образ Вани, `./data:/data:ro`) → `frontend` (nginx, `/api` → backend).
  Порты и адреса — из `.env` (`.env.example`): `PUBLIC_URL` задаёт CORS, `FRONTEND_URL` и redirect FSP ID.
  Бэкенд проброшен на `127.0.0.1:${API_PORT:-8000}` только для vite dev-сервера.
- Фронтенд: Vite 5 + React 18 + TS + Tailwind + react-query. Типы API **генерируются из OpenAPI бэкенда**
  (`npm run gen:api` → `src/lib/api-schema.ts`), поэтому моки не делал: API Вани уже работает.
- Готово: главная (демо-входы, регистрация с кодом, вход), шапка с ролью, защита маршрутов по роли, все маршруты обоих кабинетов (экраны — заглушки).
- Проверено: `npm run build` зелёный; `docker compose up -d --build` → главная, SPA-маршруты и `/api/health` через nginx; демо-вход работодателя.
- Дальше (шаг 2): экраны кандидата (профиль, FSP ID, тест, результат, категория, приглашения) и работодателя (мастер потребности, подборка с explain, приглашение).

Локально у меня 8000 и 80 заняты — в `.env`: `API_PORT=8010`, `HTTP_PORT=8088`.
