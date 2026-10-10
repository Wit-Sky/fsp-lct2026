"""backend / python — «что выведет код». Код собирается из частей, ответ вычисляется исполнением логики."""
from app.bank._base import template, var_name, names

SPEC, TOPIC = "backend", "python"


@template("backend.python.slice_sum", SPEC, TOPIC, -1.4, "number",
          "Срезы списка и sum: базовый синтаксис, ошибка обычно в границах среза → лёгкое.")
def _slice_sum(rng):
    xs = [rng.randint(1, 20) for _ in range(rng.randint(5, 7))]
    i = rng.randint(0, 2)
    j = rng.randint(i + 2, len(xs))
    n = names(rng, 1)[0]
    return {"text": "Что выведет код?", "code": f"{n} = {xs}\nprint(sum({n}[{i}:{j}]))",
            "answer": sum(xs[i:j])}


@template("backend.python.loop_mod", SPEC, TOPIC, -0.9, "number",
          "Цикл с условием по остатку: нужно аккуратно пройти range → лёгкое.")
def _loop_mod(rng):
    n, k = rng.randint(8, 30), rng.randint(2, 5)
    acc = var_name(rng, ("total", "acc", "s", "res"))
    return {"text": "Что выведет код?",
            "code": f"{acc} = 0\nfor i in range({n}):\n    if i % {k} == 0:\n        {acc} += i\nprint({acc})",
            "answer": sum(i for i in range(n) if i % k == 0)}


@template("backend.python.mutable_default", SPEC, TOPIC, 0.0, "number",
          "Изменяемый аргумент по умолчанию живёт между вызовами — классическая ловушка уровня middle.")
def _mutable_default(rng):
    calls = rng.randint(2, 5)
    fn = rng.choice(["add", "push", "collect", "remember"])
    lines = [f"def {fn}(x, acc=[]):", "    acc.append(x)", "    return acc", ""]
    lines += [f"{fn}({rng.randint(1, 9)})" for _ in range(calls - 1)]
    lines.append(f"print(len({fn}({rng.randint(1, 9)})))")
    return {"text": "Что выведет код?", "code": "\n".join(lines), "answer": calls}


@template("backend.python.dict_get", SPEC, TOPIC, 0.4, "number",
          "Генератор словаря + get со значением по умолчанию: надо понять, есть ли ключ.")
def _dict_get(rng):
    n, p = rng.randint(3, 7), rng.randint(2, 5)
    q = rng.choice([rng.randint(0, n - 1), n + rng.randint(0, 2)])
    r = rng.randint(-5, -1)
    d = {k: k * p for k in range(n)}
    return {"text": "Что выведет код?",
            "code": f"d = {{k: k * {p} for k in range({n})}}\nprint(d.get({q}, {r}) + len(d))",
            "answer": d.get(q, r) + len(d)}


@template("backend.python.late_binding", SPEC, TOPIC, 1.2, "number",
          "Позднее связывание в замыканиях: все lambda видят последнее i — ловушка уровня senior.")
def _late_binding(rng):
    n, m = rng.randint(3, 6), rng.randint(2, 9)
    j = rng.randint(0, n - 1)
    f = names(rng, 1, ("fs", "funcs", "handlers", "callbacks"))[0]
    return {"text": "Что выведет код?",
            "code": f"{f} = [lambda: i * {m} for i in range({n})]\nprint({f}[{j}]())",
            "answer": (n - 1) * m}


@template("backend.python.list_alias", SPEC, TOPIC, 1.5, "number",
          "[[0]*k]*n создаёт n ссылок на один список — алиасинг, частая ошибка даже у опытных.")
def _list_alias(rng):
    n, k, v = rng.randint(3, 6), rng.randint(2, 4), rng.randint(2, 9)
    g = names(rng, 1, ("grid", "board", "matrix", "table"))[0]
    return {"text": "Что выведет код?",
            "code": f"{g} = [[0] * {k}] * {n}\n{g}[0][0] = {v}\nprint(sum(row[0] for row in {g}))",
            "answer": n * v}
