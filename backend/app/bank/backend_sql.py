"""backend / sql — выборки, группировка, JOIN, NULL, индексы, изоляция транзакций."""
from app.bank._base import template, choice

SPEC, TOPIC = "backend", "sql"
CUSTOMERS = ["anna", "boris", "vera", "gleb", "dina", "egor", "zoya", "ilya"]


def _table(header, rows):
    w = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    fmt = lambda r: " | ".join(str(x).ljust(n) for x, n in zip(r, w))
    return "\n".join([fmt(header), "-+-".join("-" * n for n in w)] + [fmt(r) for r in rows])


@template("backend.sql.where_count", SPEC, TOPIC, -1.3, "number",
          "COUNT с WHERE по таблице на экране — базовая выборка.")
def _where_count(rng):
    rows = [(i + 1, rng.choice(CUSTOMERS), rng.randint(1, 50) * 100) for i in range(rng.randint(6, 9))]
    x = rng.choice(rows)[2]
    op = rng.choice([">", ">="])
    ans = sum(1 for r in rows if (r[2] > x if op == ">" else r[2] >= x))
    return {"text": "Таблица orders:\n" + _table(("id", "customer", "amount"), rows) + "\n\nЧто вернёт запрос?",
            "code": f"SELECT COUNT(*) FROM orders WHERE amount {op} {x};", "answer": ans}


@template("backend.sql.group_having", SPEC, TOPIC, -0.7, "number",
          "GROUP BY + HAVING: нужно сгруппировать в уме.")
def _group_having(rng):
    pool = rng.sample(CUSTOMERS, 4)
    rows = [(i + 1, rng.choice(pool), rng.randint(1, 30) * 100) for i in range(rng.randint(7, 10))]
    k = rng.randint(2, 3)
    cnt = {}
    for r in rows:
        cnt[r[1]] = cnt.get(r[1], 0) + 1
    return {"text": "Таблица orders:\n" + _table(("id", "customer", "amount"), rows) +
                    "\n\nСколько строк вернёт запрос?",
            "code": f"SELECT customer, COUNT(*)\nFROM orders\nGROUP BY customer\nHAVING COUNT(*) >= {k};",
            "answer": sum(1 for v in cnt.values() if v >= k)}


@template("backend.sql.left_join", SPEC, TOPIC, 0.1, "number",
          "LEFT JOIN размножает строки и сохраняет пользователей без заказов — частая ошибка в подсчётах.")
def _left_join(rng):
    users = [(i + 1, n) for i, n in enumerate(rng.sample(CUSTOMERS, rng.randint(3, 5)))]
    orders = [(i + 1, rng.choice(users)[0]) for i in range(rng.randint(3, 7))]
    per = {u: sum(1 for o in orders if o[1] == u) for u, _ in users}
    return {"text": "Таблица users:\n" + _table(("id", "name"), users) +
                    "\n\nТаблица orders:\n" + _table(("id", "user_id"), orders) + "\n\nЧто вернёт запрос?",
            "code": "SELECT COUNT(*)\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id;",
            "answer": sum(max(1, v) for v in per.values())}


@template("backend.sql.index_choice", SPEC, TOPIC, 0.5, "single",
          "Составной индекс: сначала равенство, потом диапазон — проверка понимания B-tree.")
def _index_choice(rng):
    t = rng.choice(["orders", "events", "payments", "sessions"])
    eq, rng_col, other = rng.sample(["user_id", "status", "created_at", "amount", "region_id", "type"], 3)
    return {"text": f"Какой индекс лучше всего ускорит запрос к большой таблице {t}?",
            "code": f"SELECT * FROM {t}\nWHERE {eq} = $1 AND {rng_col} > $2;",
            **choice(rng, f"({eq}, {rng_col})", [f"({rng_col}, {eq})", f"({other})", f"({rng_col})"])}


@template("backend.sql.null_compare", SPEC, TOPIC, 1.1, "number",
          "Трёхзначная логика: NULL <> x даёт UNKNOWN и строка отбрасывается — ловушка senior-уровня.")
def _null_compare(rng):
    vals = [rng.choice([None, 1, 2, 3]) for _ in range(rng.randint(6, 9))]
    v = rng.randint(1, 3)
    rows = [(i + 1, "NULL" if x is None else x) for i, x in enumerate(vals)]
    return {"text": "Таблица t:\n" + _table(("id", "x"), rows) + "\n\nЧто вернёт запрос?",
            "code": f"SELECT COUNT(*) FROM t WHERE x <> {v};",
            "answer": sum(1 for x in vals if x is not None and x != v)}


@template("backend.sql.isolation", SPEC, TOPIC, 1.6, "single",
          "Аномалии изоляции и минимальный уровень PostgreSQL, который их исключает — senior.")
def _isolation(rng):
    acc = rng.randint(1, 99)
    text, ans = rng.choice([
        (f"Транзакция A дважды читает SELECT balance FROM accounts WHERE id = {acc}; между чтениями транзакция B "
         f"изменила строку и закоммитила. Какой минимальный уровень изоляции PostgreSQL гарантирует, что A увидит одно и то же значение?",
         "REPEATABLE READ"),
        ("Две транзакции читают остаток дежурных врачей (2), каждая снимает одного разного врача с дежурства и коммитит — "
         "в итоге дежурных 0, хотя каждая проверяла «останется ≥ 1». Какой уровень изоляции PostgreSQL предотвратит такую аномалию (write skew)?",
         "SERIALIZABLE"),
        (f"Нужно, чтобы транзакция никогда не видела незакоммиченные изменения других транзакций (грязное чтение). "
         f"Какой минимальный уровень изоляции для этого достаточен в PostgreSQL?",
         "READ COMMITTED"),
    ])
    return {"text": text, **choice(rng, ans, ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"])}
