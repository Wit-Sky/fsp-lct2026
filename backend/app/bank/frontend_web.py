"""frontend / web — хранилища браузера, HTTP, безопасность, кэширование, debounce/throttle."""
from app.bank._base import template, choice

SPEC, TOPIC = "frontend", "web"


@template("frontend.web.storage", SPEC, TOPIC, -1.2, "single",
          "localStorage / sessionStorage / cookie — junior.")
def _storage(rng):
    key = rng.choice(["theme", "draft", "lang", "cartId", "filters"])
    text, ans = rng.choice([
        (f"Значение {key} должно пережить перезагрузку и закрытие браузера и не уходить на сервер с запросами.", "localStorage"),
        (f"Значение {key} нужно только до закрытия вкладки.", "sessionStorage"),
        (f"Значение {key} должно автоматически отправляться на сервер с каждым запросом.", "cookie"),
    ])
    return {"text": "Где хранить? " + text, **choice(rng, ans, ["localStorage", "sessionStorage", "cookie", "IndexedDB"])}


@template("frontend.web.status", SPEC, TOPIC, -0.6, "single",
          "Как фронтенду реагировать на коды 401/403/404/500.")
def _status(rng):
    text, ans = rng.choice([
        ("API ответил 401 — что сделать на фронтенде?", "отправить пользователя на вход / обновить токен"),
        ("API ответил 404 на /profile/<id> — что показать?", "страницу «не найдено»"),
        ("API ответил 403 — что показать?", "сообщение «нет доступа»"),
        ("API ответил 422 на отправку формы — что сделать?", "показать ошибки валидации у полей формы"),
        ("API ответил 500 — что показать?", "сообщение об ошибке сервера и предложение повторить позже"),
        ("API ответил 429 — что сделать?", "подождать (Retry-After) и повторить запрос позже"),
    ])
    pool = ["отправить пользователя на вход / обновить токен", "страницу «не найдено»", "сообщение «нет доступа»",
            "показать ошибки валидации у полей формы", "сообщение об ошибке сервера и предложение повторить позже",
            "подождать (Retry-After) и повторить запрос позже", "повторять запрос в цикле без паузы"]
    return {"text": text, **choice(rng, ans, rng.sample(pool, len(pool)))}


@template("frontend.web.xss", SPEC, TOPIC, 0.1, "single",
          "Безопасная вставка пользовательского текста — XSS.")
def _xss(rng):
    field = rng.choice(["комментарий", "имя пользователя", "отзыв", "название задачи"])
    text, ans, wrong = rng.choice([
        (f"Нужно вывести {field} из API в элемент el без риска XSS.", "el.textContent = value",
         ["el.innerHTML = value", "el.outerHTML = value", "document.write(value)"]),
        (f"В React нужно показать {field} от пользователя. Как безопасно?", "{value} внутри JSX",
         ["dangerouslySetInnerHTML={{__html: value}}", "eval(value)", "ref.current.innerHTML = value"]),
    ])
    return {"text": text, **choice(rng, ans, wrong)}


@template("frontend.web.cache_control", SPEC, TOPIC, 0.6, "single",
          "Cache-Control: no-store / no-cache / immutable — middle.")
def _cache(rng):
    h = "".join(rng.choice("0123456789abcdef") for _ in range(8))
    text, ans = rng.choice([
        ("Ответ с персональными данными нельзя сохранять ни в каком кэше.", "no-store"),
        ("Кэшировать можно, но перед использованием всегда сверяться с сервером.", "no-cache"),
        (f"Файл /assets/app.{h}.js с хэшем в имени никогда не меняется.", "max-age=31536000, immutable"),
    ])
    return {"text": "Какое значение Cache-Control подходит? " + text,
            **choice(rng, ans, ["no-store", "no-cache", "max-age=31536000, immutable", "private, max-age=0"])}


@template("frontend.web.debounce", SPEC, TOPIC, 1.1, "number",
          "Debounce: обработчик срабатывает после паузы — нужно смоделировать по времени.")
def _debounce(rng):
    d = rng.choice([200, 300, 500])
    t, times = 0, []
    for _ in range(rng.randint(6, 9)):
        t += rng.choice([50, 100, 150, 250, 400, 600])
        times.append(t)
    calls = sum(1 for a, b in zip(times, times[1:]) if b - a >= d) + 1
    return {"text": f"Поле поиска: обработчик обёрнут в debounce с задержкой {d} мс (вызов в конце паузы). "
                    f"Пользователь нажимает клавиши в моменты (мс): {', '.join(map(str, times))}. Сколько раз выполнится поиск?",
            "answer": calls}


@template("frontend.web.cors_cookie", SPEC, TOPIC, 1.5, "single",
          "Cookies между сайтами: SameSite, Secure, credentials — senior.")
def _cors_cookie(rng):
    text, ans, wrong = rng.choice([
        ("Фронтенд на app.site.ru, API на api.other.ru. Какой атрибут cookie нужен, чтобы браузер отправлял её на API в fetch с credentials?",
         "SameSite=None; Secure", ["SameSite=Lax", "SameSite=Strict", "HttpOnly без SameSite"]),
        ("Какой атрибут cookie не даёт прочитать её из JavaScript (document.cookie)?",
         "HttpOnly", ["Secure", "SameSite=Strict", "Path=/"]),
        ("Какой fetch-параметр нужен, чтобы браузер отправил cookies на другой origin?",
         "credentials: 'include'", ["mode: 'no-cors'", "cache: 'reload'", "credentials: 'omit'"]),
        ("Запрос с credentials на другой origin. Какое значение Access-Control-Allow-Origin браузер НЕ примет?",
         "*", ["точный origin фронтенда", "https://app.site.ru, если запрос именно оттуда", "origin из белого списка, совпавший с Origin"]),
        ("Что браузер отправит перед fetch PUT с Content-Type: application/json на другой origin?",
         "предварительный запрос OPTIONS (preflight)", ["HEAD", "GET без тела", "ничего — сразу PUT"]),
        ("Что означает атрибут cookie Secure?",
         "cookie отправляется только по HTTPS", ["cookie нельзя прочитать из JavaScript", "cookie не уходит на другие сайты",
                                                 "браузер шифрует значение cookie"]),
        ("Какой заголовок ответа, кроме Access-Control-Allow-Origin, нужен, чтобы JS получил ответ на запрос с credentials?",
         "Access-Control-Allow-Credentials: true", ["Access-Control-Allow-Headers: *", "Access-Control-Max-Age: 600", "Vary: Cookie"]),
    ])
    return {"text": text, **choice(rng, ans, wrong)}
