"""backend / http — коды ответа, методы, кэш, CORS, ограничение частоты."""
from app.bank._base import template, choice

SPEC, TOPIC = "backend", "http"
ENTITIES = ["заказ", "пользователь", "товар", "платёж", "отзыв", "документ", "билет"]
PATHS = {"заказ": "orders", "пользователь": "users", "товар": "products", "платёж": "payments",
         "отзыв": "reviews", "документ": "documents", "билет": "tickets"}
CODES = ["200", "201", "204", "301", "304", "400", "401", "403", "404", "409", "412", "422", "429", "500", "503"]


def _code_q(rng, scenarios):
    ent = rng.choice(ENTITIES)
    text, code = rng.choice(scenarios)
    text = text.format(e=ent, p=PATHS[ent], id=rng.randint(10, 9999))
    return {"text": f"Какой HTTP-код должен вернуть API? {text}",
            **choice(rng, code, rng.sample([c for c in CODES if c != code], 6))}


@template("backend.http.codes_basic", SPEC, TOPIC, -1.4, "single",
          "Базовые коды 201/204/401/404 — знает любой junior.")
def _codes_basic(rng):
    return _code_q(rng, [
        ("POST /api/{p} успешно создал объект «{e}».", "201"),
        ("GET /api/{p}/{id}: объекта «{e}» с таким id нет.", "404"),
        ("Запрос к /api/{p} пришёл без токена авторизации.", "401"),
        ("DELETE /api/{p}/{id} выполнен, тело ответа не нужно.", "204"),
    ])


@template("backend.http.methods", SPEC, TOPIC, -0.9, "single",
          "Семантика методов REST: GET/PUT/PATCH/DELETE.")
def _methods(rng):
    ent = rng.choice(ENTITIES)
    text, ans = rng.choice([
        ("Нужно частично обновить объект «{e}» (изменить одно поле).", "PATCH"),
        ("Нужно полностью заменить объект «{e}» новым представлением.", "PUT"),
        ("Нужно получить объект «{e}» без побочных эффектов.", "GET"),
        ("Нужно удалить объект «{e}».", "DELETE"),
    ])
    return {"text": "Какой HTTP-метод подходит? " + text.format(e=ent),
            **choice(rng, ans, [m for m in ["GET", "POST", "PUT", "PATCH", "DELETE"] if m != ans])}


@template("backend.http.codes_middle", SPEC, TOPIC, 0.1, "single",
          "Различие 401/403, 409, 422, 429 — типичный вопрос на middle.")
def _codes_middle(rng):
    return _code_q(rng, [
        ("Пользователь авторизован, но пытается изменить чужой объект «{e}».", "403"),
        ("POST /api/users: пользователь с таким email уже существует.", "409"),
        ("Тело запроса синтаксически верно, но поле salary_from больше salary_to.", "422"),
        ("Клиент превысил лимит запросов к /api/{p} в минуту.", "429"),
    ])


@template("backend.http.cache_codes", SPEC, TOPIC, 0.6, "single",
          "Условные запросы и деградация: 304, 412, 503 — требуют знания заголовков.")
def _cache_codes(rng):
    return _code_q(rng, [
        ("GET /api/{p}/{id} с If-None-Match, ETag объекта «{e}» не изменился.", "304"),
        ("PUT /api/{p}/{id} с If-Match, но объект «{e}» уже изменил другой клиент (ETag другой).", "412"),
        ("Сервис /api/{p} на обслуживании, клиенту стоит повторить позже (Retry-After).", "503"),
    ])


@template("backend.http.cors", SPEC, TOPIC, 1.1, "single",
          "CORS: preflight, credentials, Vary — частая причина ошибок интеграции фронта и бэка.")
def _cors(rng):
    origin = f"https://{rng.choice(['app', 'admin', 'lk', 'portal'])}.{rng.choice(['example', 'company', 'shop'])}.ru"
    text, ans, wrong = rng.choice([
        (f"Фронтенд на {origin} шлёт PUT с JSON. Каким методом браузер сделает предварительный (preflight) запрос?",
         "OPTIONS", ["HEAD", "GET", "PUT"]),
        (f"Запрос с {origin} идёт с cookies (credentials: 'include'). Какое значение Access-Control-Allow-Origin допустимо?",
         origin, ["*", "null", "same-origin"]),
        (f"Сервер отвечает разным origin разным Access-Control-Allow-Origin. Какой заголовок нужен, чтобы CDN не отдал чужой ответ из кэша?",
         "Vary: Origin", ["Cache-Control: public", "Access-Control-Max-Age: 600", "Pragma: no-cache"]),
    ])
    return {"text": text, **choice(rng, ans, wrong)}


@template("backend.http.token_bucket", SPEC, TOPIC, 1.5, "number",
          "Token bucket: нужно понять ёмкость (всплеск) и скорость пополнения — senior-уровень ограничения нагрузки.")
def _token_bucket(rng):
    cap, rate, t = rng.randint(5, 20), rng.randint(1, 5), rng.randint(3, 10)
    return {"text": (f"Ограничитель запросов — token bucket: ёмкость {cap} токенов, пополнение {rate} токен(а) в секунду, "
                     f"в момент 0 корзина полная. Клиент шлёт запросы непрерывно и максимально часто. "
                     f"Сколько запросов будет пропущено за первые {t} секунд (включая момент 0)?"),
            "answer": cap + rate * t}
