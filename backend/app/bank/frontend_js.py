"""frontend / js — вывод кода, приведение типов, замыкания, event loop."""
from app.bank._base import template, choice, names

SPEC, TOPIC = "frontend", "js"


@template("frontend.js.filter_len", SPEC, TOPIC, -1.3, "number",
          "filter + length — базовая работа с массивами.")
def _filter_len(rng):
    xs = [rng.randint(1, 30) for _ in range(rng.randint(6, 9))]
    k = rng.randint(2, 5)
    n = names(rng, 1)[0]
    return {"text": "Что выведет код?",
            "code": f"const {n} = {xs};\nconsole.log({n}.filter(x => x % {k} === 0).length);",
            "answer": sum(1 for x in xs if x % k == 0)}


@template("frontend.js.typeof", SPEC, TOPIC, -0.8, "single",
          "typeof для null, массивов, NaN — известные «странности» JS уровня junior.")
def _typeof(rng):
    expr, ans = rng.choice([("null", "object"), ("[]", "object"), ("NaN", "number"), ("undefined", "undefined"),
                            ("() => 1", "function"), ("{}", "object"), (f"'{rng.randint(1, 99)}'", "string"),
                            (f"{rng.randint(1, 99)}n", "bigint")])
    return {"text": "Что выведет код?", "code": f"console.log(typeof {expr});",
            **choice(rng, f'"{ans}"', ['"object"', '"number"', '"undefined"', '"string"', '"function"', '"null"'])}


@template("frontend.js.coercion", SPEC, TOPIC, 0.1, "number",
          "Приведение типов: + со строкой — конкатенация, − приводит к числу.")
def _coercion(rng):
    p, q, r = rng.randint(1, 9), rng.randint(0, 9), rng.randint(1, 9)
    return {"text": "Что выведет код?", "code": f'console.log("{p}" + {q} - {r});',
            "answer": int(f"{p}{q}") - r}


@template("frontend.js.var_closure", SPEC, TOPIC, 0.6, "number",
          "var в цикле и замыкания: у всех функций одна переменная i — классика middle.")
def _var_closure(rng):
    n, j = rng.randint(3, 7), 0
    j = rng.randint(0, n - 1)
    f = names(rng, 1, ("fns", "handlers", "cbs", "list"))[0]
    return {"text": "Что выведет код?",
            "code": f"const {f} = [];\nfor (var i = 0; i < {n}; i++) {{\n  {f}.push(() => i);\n}}\nconsole.log({f}[{j}]());",
            "answer": n}


@template("frontend.js.event_loop", SPEC, TOPIC, 1.2, "order",
          "Порядок выполнения: синхронный код → микрозадачи (Promise) → макрозадачи (setTimeout) — senior-база.")
def _event_loop(rng):
    labels = rng.sample(["A", "B", "C", "D", "E", "F", "G"], 5)
    kinds = ["sync", "sync"] + [rng.choice(["micro", "macro"]) for _ in range(3)]
    if "micro" not in kinds:
        kinds[2] = "micro"
    if "macro" not in kinds:
        kinds[3] = "macro"
    rng.shuffle(kinds)
    lines = []
    for lab, k in zip(labels, kinds):
        if k == "sync":
            lines.append(f"console.log('{lab}');")
        elif k == "micro":
            lines.append(f"Promise.resolve().then(() => console.log('{lab}'));")
        else:
            lines.append(f"setTimeout(() => console.log('{lab}'), 0);")
    order = ([l for l, k in zip(labels, kinds) if k == "sync"] + [l for l, k in zip(labels, kinds) if k == "micro"]
             + [l for l, k in zip(labels, kinds) if k == "macro"])
    return {"text": "Расположите буквы в порядке, в котором их выведет код.", "code": "\n".join(lines),
            "options": order, "answer": order}


def _parse_int(s: str, radix: int):
    if radix == 0:
        radix = 10
    if radix < 2 or radix > 36:
        return None
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"[:radix]
    out = ""
    for ch in s:
        if ch.lower() in digits:
            out += ch
        else:
            break
    return int(out, radix) if out else None


@template("frontend.js.map_parseint", SPEC, TOPIC, 1.6, "number",
          "map передаёт индекс вторым аргументом, parseInt трактует его как основание — senior-ловушка.")
def _map_parseint(rng):
    xs = [str(rng.randint(1, 15)) for _ in range(rng.randint(4, 6))]
    nan = sum(1 for i, s in enumerate(xs) if _parse_int(s, i) is None)
    arr = "[" + ", ".join(f"'{s}'" for s in xs) + "]"
    return {"text": "Сколько элементов результата будут NaN?", "code": f"const r = {arr}.map(parseInt);\nconsole.log(r);",
            "answer": nan}
