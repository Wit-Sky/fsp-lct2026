# 8. Сборка, развёртывание и локальный запуск

## Стенд для жюри

- Адрес: **https://81-26-180-5.sslip.io** (Swagger: `/api/docs`).
- Демо-входы — кнопки «Войти как кандидат» и «Войти как работодатель» на главной (без пароля, `POST /api/auth/demo/{role}`).
  Те же аккаунты с паролем: `candidate@demo.fsp` / `demo`, `employer@demo.fsp` / `demo`.
- На стенде включён демо-режим: код подтверждения email показывается на экране (имитация письма),
  кулдаун повторного теста на тот же грейд — 2 минуты вместо 30 дней.
- Сервер: Yandex Cloud, Ubuntu 24.04, 2 vCPU / 4 ГБ ОЗУ, HTTPS — Let's Encrypt через Caddy.

## Локальный запуск одной командой

Нужны Docker и Docker Compose v2.

```
git clone https://github.com/Wit-Sky/fsp-lct2026
cd fsp-lct2026
cp .env.example .env        # можно пропустить: без .env работают значения по умолчанию
docker compose up -d --build
```

После старта: веб-приложение — http://localhost/, API — http://localhost/api, Swagger — http://localhost/api/docs.
База PostgreSQL и демо-данные (300 синтетических кандидатов, банк шаблонов заданий, демо-аккаунты) создаются при первом запуске.

Сервисы `docker-compose.yml`:

| Сервис | Что делает |
|---|---|
| `db` | PostgreSQL 16 (`postgres:16-alpine`), данные в томе `pgdata` |
| `backend` | FastAPI + SQLAlchemy 2 async, миграции alembic, порт 8000 только на 127.0.0.1 |
| `frontend` | сборка React (Vite) и nginx: статика и прокси `/api` на бэкенд |
| `caddy` | HTTPS-прокси, включается профилем `https` (только на стенде) |

Переменные `.env`:

| Переменная | Назначение |
|---|---|
| `PUBLIC_URL` | внешний адрес стенда (для CORS и адреса возврата FSP ID) |
| `HTTP_PORT` | порт nginx фронтенда |
| `POSTGRES_PASSWORD`, `JWT_SECRET` | секреты; на стенде генерируются случайно и не покидают сервер |
| `DEMO_MODE` | 1 — код подтверждения email показывается в ответе (имитация письма) |
| `DEMO_COOLDOWN_MIN` | кулдаун в минутах для демо; 0 — боевые 30 дней |

## Развёртывание на сервере (как поднят стенд)

1. Один раз: `deploy/bootstrap.sh` на чистой ВМ Ubuntu ставит Docker, добавляет swap 2 ГБ (сборка фронтенда на маленькой ВМ),
   создаёт пользователя `deploy` с ключом GitHub Actions и файл `.env` со случайными секретами.
   Домен без покупки — `<ip-через-дефисы>.sslip.io`.
2. Дальше автоматически: `.github/workflows/deploy.yml` при пуше в `main` проверяет сборку фронтенда,
   копирует код на ВМ (rsync), выполняет `docker compose up -d --build`, чистит старые образы (диск ВМ 9 ГБ)
   и ждёт ответа `/api/health`. Секреты репозитория: `DEPLOY_HOST`, `DEPLOY_SSH_KEY`.

## Валидация и документация

```
python -X utf8 validation/run_all.py     # validation/results.md, results.json, графики в validation/img
python -X utf8 docs/build_pdf.py         # этот PDF
```
