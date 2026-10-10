# CONTRACT.md — общий контракт для четырёх Claude Code (положить в корень репозитория)

Команда: Евгений (капитан: фронтенд, сервер, сдача), Ваня (бэкенд), Антон (данные, валидация, документация, презентация),
Стася (сквозное тестирование «как жюри», независимая разметка пар). Глоссарий — `CONTEXT.md`, решения — `docs/adr/`.

Любое изменение схемы или API — сначала правка этого файла и сообщение в чат команды.

## 1. Стек и структура
- Backend: Python 3.12, FastAPI, **PostgreSQL 16, SQLAlchemy 2 async + asyncpg, миграции alembic** (как в «Полёт БВС» — для последующего переноса),
  pydantic v2, passlib[bcrypt], PyJWT. OpenAPI — автоматически `/docs`. Ядро `testing` и `matching` — чистые функции без БД (раздел 8.3).
- Frontend: Vite + React + TypeScript, react-router, без UI-фреймворков тяжелее Tailwind. Цвета ФСП: #520978, #310F53, #FF0053, #FC3777, #8A83D1, #FFD6E4, #1C1D22, шрифт Montserrat.
- Один `docker-compose.yml`: `db` (postgres:16-alpine, том `pgdata`, healthcheck) + `backend` (порт 8000, при старте `alembic upgrade head` и сид)
  + `frontend` (nginx, порт 80, проксирует `/api` → backend). Без GPU, без LLM в обязательном пути.
```
/backend/app/{main.py, db.py, models.py, schemas.py, auth.py, routers/, seed.py}
/backend/app/services/{testing.py, profile.py, matching.py}   # три модуля для переноса, см. раздел 9
/backend/alembic/               # миграции
/backend/app/bank/*.py          # шаблоны заданий
/frontend/src/{pages/candidate, pages/employer, api.ts}
/data/                          # синтетика: candidates.json, needs.json, pairs_labeled.json, pairs_labeled_stasya.json
/validation/                    # скрипты метрик и отчёт results.md
/docs/                          # md → pdf;  /docs/adr/ — архитектурные решения
/CONTEXT.md                     # глоссарий (единый язык)
```

## 2. Справочники
- Специализации (MVP): `backend`, `frontend`; третья — `bas` («БАС-разработчик»): в каталоге и данных сразу, полноценный банк заданий — если успеем.
  `ml` не делаем.
- Грейды: `junior`, `middle`, `senior`. Порог θ (см. 3): junior ≥ −0,5; middle ≥ 0,5; senior ≥ 1,5.
- Статус грейда: `confirmed` | `unconfirmed` | `none`.
- Кулдаун: повторный тест на тот же или более высокий грейд — не раньше чем через 30 дней (на демо — флаг `DEMO_COOLDOWN_MIN=2` минуты). Тест на грейд ниже сразу после провала — без ожидания.

## 3. Механика тестирования (ядро критерия 25 %)
**Параметрические шаблоны + калиброванная сложность (модель Раша).**
- Шаблон задания = функция `generate(seed) -> {text, options|input, answer}` + метаданные `{id, spec, topic, difficulty_b, kind}`.
  Сид = hash(candidate_id, attempt_id, template_id) — у каждого кандидата свои числа, имена, фрагменты кода, порядок вариантов; правильный ответ вычисляется кодом. Сложность задаёт шаблон, а не случайность — поэтому разные варианты сопоставимы.
- Виды: `single` (выбор), `number` (числовой ответ, например «что выведет код»), `order` (упорядочить шаги). Свободный текст — только в регулярных заданиях работодателя.
- Сборка теста: 10 заданий за 5 минут (экспресс), темы покрывают специализацию; первые 3 задания около заявленного грейда, далее адаптивно: верно — шаблон сложнее, неверно — проще.
- Оценка θ — оценка максимального правдоподобия по Рашу при известных b (с ограничением [−3; 3]). Грейд подтверждён, если θ ≥ порога заявленного грейда. Если θ выше порога следующего — предложить «тест на повышение».
- Калибровка b: начальные значения экспертно (junior ≈ −1, middle ≈ 0, senior ≈ 1,5), уточняются на симуляции (валидация).
- Защита от утечки: (1) значения уникальны для кандидата — слитый ответ бесполезен; (2) пул ≥ 6 шаблонов на тему, случайный выбор; (3) лимит времени на задание; (4) статистика шаблона: если доля верных резко растёт — шаблон помечается «скомпрометирован» (концепция).

## 4. Механика подбора (ядро критерия 35 %)
**«Заявка на команду»:** работодатель описывает потребность → система показывает подходящие категории с числом кандидатов → ранжированная подборка с объяснением → адресное приглашение с зарплатой → кандидат принимает → открываются контакты.
Скор кандидата для потребности (0–100):
```
score = 100 * ( 0,40 * stack_match        # доля требуемых навыков, подтверждённых профилем (вес навыка из потребности)
              + 0,30 * test_score         # θ нормированная в [0;1] внутри категории
              + 0,15 * fsp_score          # 0, если истории ФСП нет; призовые места и число стартов, релевантная дисциплина ×1,5
              + 0,10 * freshness          # давность теста и регулярных заданий
              + 0,05 * pref_match )       # формат работы, город, зарплатные ожидания попадают в вилку
× 0,6, если грейд не подтверждён
```
- Жёсткий фильтр: специализация и грейд из категории (грейд ±0 по умолчанию, флажок «соседние грейды»).
- Ответ содержит `explain: [{factor, weight, value, text}]`, например «Подтвердил middle (θ = 0,9, 82-й процентиль категории)», «Призёр ФСП по продуктовому программированию, 2026».
- Уточнение фильтров не сбрасывает подборку: `GET /searches/{id}` хранит исходный запрос, фильтры — параметры.

## 5. Модель данных (минимум)
- `User(id, email, password_hash, role: candidate|employer, email_verified, created_at)`
- `ExternalIdentity(id, user_id, provider: 'fsp', subject, linked_at, claims: json)` — внешняя учётная запись (FSP ID); unique(provider, subject)
- `CandidateProfile(user_id, full_name, birth_date, phone, telegram, city, work_format, salary_expect_from, skills: [str], experience_years, about, consent_pd: bool, parent_consent: bool, visible_fields: json)`
  Младше 18 лет (по `birth_date`) → в профиле флаг «нужно согласие родителя» (`parent_consent`), работодатель видит пометку «несовершеннолетний».
- `VerifiedResult(id, user_id, source: 'fsp', external_id, event, discipline, year, place?, role: winner|prize|participant, team: bool, imported_at)` —
  **подтверждённый результат** из источника результатов (сейчас FSP ID, имитация). Не «достижение»: см. `CONTEXT.md`.
- `GradeAttempt(id, user_id, spec, claimed_grade, started_at, finished_at, theta, result: confirmed|failed, items: json)`
- `Category(user_id, spec, grade, status, theta, confirmed_at, next_attempt_at)`
- `Employer(id, owner_id, name, inn?, field, description, contacts)` — **работодатель** (в UI «Профиль компании»). Не «Организация»: см. `CONTEXT.md`.
- `Need(id, employer_id, title, spec, grade, skills: [{name, weight}], description, salary_from, salary_to, salary_type: gross|net, work_format)` — она же вакансия при `published=true`
- `Invitation(id, need_id?, employer_id, candidate_id, message, salary_from, salary_to, salary_type, contact_method, status: sent|viewed|accepted|declined, created_at, updated_at)`
- `Application(id, need_id, candidate_id, status: sent|viewed|accepted|declined)` — дополнительный сценарий
- `Task(id, employer_id, spec, text, kind)` и `TaskAnswer(...)` — регулярные задания, если успеем

## 6. API (префикс `/api`, JWT в заголовке `Authorization: Bearer`)
| Метод | Путь | Кто | Суть |
|---|---|---|---|
| POST | /auth/register | все | email, password, role → код подтверждения (на демо возвращается в ответе и пишется в лог) |
| POST | /auth/verify | все | email, code |
| POST | /auth/login | все | → token |
| GET | /auth/fsp/authorize, /auth/fsp/callback | кандидат | имитация OIDC FSP ID: создаёт ExternalIdentity и импортирует VerifiedResult |
| POST | /auth/demo/{role} | все | мгновенный вход демо-аккаунтом для жюри |
| GET/PUT | /me/profile | кандидат | профиль, согласие, приватность |
| POST | /me/resume/parse | кандидат | загрузка PDF → черновик полей (pdfplumber + регулярные выражения, LLM опционально) |
| GET | /me/profile.pdf | кандидат | стандартизированный PDF-профиль |
| GET | /me/results | кандидат | подтверждённые результаты (по источникам) |
| GET | /me/category | кандидат | текущая категория, история попыток, `next_attempt_at` |
| POST | /tests/start | кандидат | {spec, claimed_grade} → attempt_id, первое задание (403 при кулдауне с датой) |
| POST | /tests/{id}/answer | кандидат | {item_id, answer} → следующее задание или итог |
| GET | /tests/{id}/result | кандидат | θ, грейд, разбор |
| GET | /me/invitations; POST /invitations/{id}/accept, /decline | кандидат | |
| GET | /vacancies; POST /vacancies/{id}/apply; GET /me/applications | кандидат | дополнительно |
| GET/PUT | /employer | работодатель | профиль компании |
| POST | /needs | работодатель | создать потребность → search_id |
| GET | /needs/{id}/categories | работодатель | категории с количеством кандидатов |
| GET | /needs/{id}/matches?grade_adj=&fsp_only=&skills=&limit= | работодатель | ранжированная подборка с `explain`, контакты скрыты |
| GET | /candidates?spec=&grade=&skills=&fsp=&status= | работодатель | поиск по банку |
| GET | /candidates/{id} | работодатель | карточка; контакты только при accepted-приглашении или отклике |
| POST | /invitations | работодатель | {candidate_id, need_id?, message, salary_from, salary_to, salary_type, contact_method} |
| GET | /employer/invitations | работодатель | статусы |
| POST | /needs/{id}/publish; GET /needs/{id}/applications | работодатель | дополнительно |

Ошибки: `{detail: str, code: str}`; 401, 403 (чужие данные, кулдаун), 404, 422.

## 8. Стыки между частями (не менять без согласования)

### 8.1. Словари (`backend/app/catalog.py`, генератор данных берёт их отсюда же)
- Навыки `backend`: Python, Go, Java, FastAPI, Django, Spring, PostgreSQL, Redis, Kafka, Docker, Kubernetes, Linux, REST, gRPC, SQL.
- Навыки `frontend`: JavaScript, TypeScript, React, Vue, Next.js, Redux, HTML, CSS, Vite, Webpack, Jest, REST, Figma, Accessibility.
- Навыки `bas`: Python, C++, Embedded C, Linux, MAVLink, ArduPilot, PX4, ROS 2, GNSS, Kalman filter, Computer Vision, Docker, SQL.
- Дисциплины ФСП: «продуктовое программирование», «алгоритмическое программирование», «программирование систем информационной безопасности», «программирование робототехники», «программирование беспилотных авиационных систем».
- Релевантность дисциплины (множитель 1,5): backend и frontend ← продуктовое; bas ← программирование БАС и программирование робототехники.
  Остальные — множитель 1,0 (все дисциплины равноценны, буст только за близость).
- Роль в соревновании: `winner` | `prize` | `participant`. Формат работы: `office` | `remote` | `hybrid`.

### 8.2. Файлы данных (`/data`, делает Антон, читает `backend/app/seed.py`)
- `employers.json`: `[{id, name, inn, field, description, contacts, owner_email}]`
- `candidates.json`: `[{id, email, full_name, birth_date, phone, telegram, city, work_format, salary_expect_from, experience_years, spec, claimed_grade, skills: [str], about, fsp_id: str|null, results: [{source: "fsp", external_id, event, discipline, year, place: int|null, role, team: bool}], theta_true}]`
  Распределение spec: backend 45 % / frontend 45 % / bas 10 %. Около 5 % кандидатов — 16–17 лет.
  `theta_true` — только для валидации, в БД и API не попадает.
- `needs.json`: `[{id, employer_id, title, spec, grade, skills: [{name, weight}], description, salary_from, salary_to, salary_type, work_format, published: bool}]`
- `pairs_labeled.json`: `{"<need_id>": {"<candidate_id>": 2|1}}` — 2 = точно подходит, 1 = частично; правило разметки в `validation/README.md`.
- `pairs_labeled_stasya.json`: тот же формат — независимая ручная разметка Стаси по 10 потребностям (по карточкам, без θ_true и без скора);
  Антон считает согласие разметчиков (каппа Коэна) и пишет в отчёт валидации.
- `fsp_registry.json`: «реестр ФСП» для имитации FSP ID: `[{fsp_id, full_name, email, results: [...]}]`.

### 8.3. Чистые функции ядра (делает Ваня, вызывает валидация Антона; без БД, без FastAPI)
```python
# backend/app/services/testing.py
TEMPLATES: dict[str, Template]          # Template: id, spec, topic, b: float, kind, generate(seed: int) -> Item
#   Item: {item_id, template_id, text, kind, options: list|None, answer (только на сервере)}
def build_attempt(candidate_id: int, spec: str, claimed_grade: str, attempt_no: int) -> dict   # состояние попытки
def next_item(state: dict) -> dict | None                                                       # None — тест окончен
def submit(state: dict, item_id: str, answer) -> bool                                           # верно/неверно, адаптирует сложность
def estimate_theta(responses: list[tuple[float, bool]]) -> float                                # (b, верно) → θ по Рашу, [−3; 3]
def grade_from_theta(theta: float) -> str | None                                                # пороги из раздела 2
def simulate_attempt(candidate_id: int, spec: str, claimed_grade: str, theta_true: float,
                     attempt_no: int, rng_seed: int) -> dict
#   → {theta, grade, confirmed: bool, items: [{template_id, b, correct, variant_hash}]}
#   ответ «кандидата» верен с вероятностью 1 / (1 + exp(−(theta_true − b)))

# backend/app/services/profile.py — импорт подтверждённых результатов из источника, без FastAPI
def import_results(source: str, claims: dict, registry: list[dict]) -> list[dict]   # → записи VerifiedResult
def fsp_score(results: list[dict], spec: str) -> tuple[float, list[dict]]            # 0..1 + explain; [] → 0 и «нет истории ФСП»

# backend/app/services/matching.py
def score(need: dict, cand: dict, now=None) -> tuple[float, list[dict]]
#   cand = поля candidates.json + {grade, status, theta, tested_at}; → (0..100, explain)
#   fsp-компонент берёт из profile.fsp_score — результат передаётся данными, не импортом моделей
def rank(need: dict, cands: list[dict], grade_adj: bool = False, fsp_only: bool = False,
         extra_skills: list[str] | None = None, limit: int = 50) -> list[dict]
#   → [{candidate_id, score, explain}] по убыванию
def keyword_baseline(need: dict, cands: list[dict], limit: int = 50) -> list[dict]   # базовая линия для сравнения
```
Импорт из корня репозитория: `sys.path.insert(0, "backend")`, затем `from app.services import testing, matching`.

### 8.4. Git
- Репозиторий — **публичный GitHub** (организатор: закрытый проверить не смогут), лицензия **MIT** в корне.
  До публикации каждый участник пишет в чат команды согласие, что код можно использовать в собственных продуктах участников.
- Ветки: `backend` (Ваня), `frontend` (Евгений), `data-docs` (Антон); Стася — только issues и `data/pairs_labeled_stasya.json` через Антона.
  В `main` — слияние своей ветки каждые 2–3 часа и в контрольные точки.
- Чужие папки не править. `CONTRACT.md` — только по договорённости в общем чате.
- Без `push --force`, без секретов в репозитории (`.env.example` вместо `.env`).
- **После 11.10 23:59 МСК — ни одного коммита.**

### 8.5. Контрольные точки (МСК)
| Когда | Ваня | Евгений | Антон | Стася |
|---|---|---|---|---|
| 10.10 23:59 | каркас FastAPI + Postgres + первая миграция, все эндпоинты-заглушки, `TEMPLATES` хотя бы по 1 на тему | каркас фронта на моках, docker-compose | `data/*.json` первая версия | — |
| 11.10 04:00 | тесты, подбор, приглашения — по-настоящему; черновик банка `bas` + `docs/bas_samples.md` — Евгению на вычитку | все экраны на моках | валидация запускается на настоящем `testing.py` | — |
| 11.10 12:00 | всё в `main`, pytest зелёный | фронт на настоящем API, стенд развёрнут | цифры валидации, черновик документации | разметка 10 потребностей сдана Антону; старт прогонов «как жюри» |
| 11.10 18:00 | **заморозка функций**, только исправления | то же | видео, презентация, PDF | повторный прогон после исправлений |
| 11.10 22:00 | — | загрузка на платформу | всё отдано Евгению | финальная проверка ссылок в инкогнито |

## 7. Демо для жюри
- Демо-аккаунты: `candidate@demo.fsp`, `employer@demo.fsp` (кнопки «Войти как …» на главной), сид: 300 кандидатов, 10 компаний, 30 потребностей, у ~40 % кандидатов есть ФСП, у ~60 % нет.
- Экспресс-тест: 10 заданий, 5 минут.

## 9. Перенос в «Полёт БВС» (после хакатона)
Подробно — `docs/adr/0001-modules-for-polet-bvs.md`.
- Три модуля с чистыми границами: `testing` (банк шаблонов, Раш, грейд, кулдаун), `profile` (внешние учётные записи и подтверждённые результаты),
  `matching` (подбор, explain, приглашения). **Друг друга не импортируют** — обмен только словарями/pydantic-схемами. Роутеры FastAPI — тонкие.
- Код «Полёт БВС» в этот репозиторий **не копировать** (регламент ЛЦТ п. 2.4 и 5.11). Повторять только соглашения: async-сессии, alembic, стиль моделей.
- Материалы и данные ФСП из ТЗ (брендбук, тексты ТЗ) в «Полёт БВС» не переносятся (регламент п. 6.3.5). Свою синтетику и свой код — можно.
- Термины — строго по `CONTEXT.md`: подтверждённый результат ≠ награда; работодатель ≠ организация.
