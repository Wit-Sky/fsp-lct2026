"""backend / arch — сложность алгоритмов, кэш, очереди, ёмкость системы."""
from app.bank._base import template, choice, var_name

SPEC, TOPIC = "backend", "arch"
BIG_O = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"]


@template("backend.arch.loops_o", SPEC, TOPIC, -1.2, "single",
          "Сложность простого или вложенного цикла — базовая асимптотика.")
def _loops_o(rng):
    a, b = var_name(rng, ("i", "j", "k")), "q"
    variant = rng.choice(["single", "nested", "const"])
    if variant == "single":
        code, ans = f"for {a} in range(n):\n    total += xs[{a}]", "O(n)"
    elif variant == "nested":
        code, ans = f"for {a} in range(n):\n    for {b} in range(n):\n        cnt += xs[{a}] == xs[{b}]", "O(n²)"
    else:
        code, ans = f"for {a} in range({rng.randint(3, 50)}):\n    total += xs[{a}]", "O(1)"
    return {"text": "Какова временная сложность фрагмента (n = len(xs))?", "code": code,
            **choice(rng, ans, BIG_O)}


@template("backend.arch.mul_steps", SPEC, TOPIC, -0.6, "number",
          "Цикл с умножением шага — подсчёт итераций, шаг к пониманию логарифма.")
def _mul_steps(rng):
    n, k = rng.randint(20, 900), rng.choice([2, 3])
    i, steps = 1, 0
    while i < n:
        i *= k
        steps += 1
    return {"text": "Сколько раз выполнится тело цикла?",
            "code": f"i = 1\nsteps = 0\nwhile i < {n}:\n    i *= {k}\n    steps += 1\nprint(steps)", "answer": steps}


@template("backend.arch.nlogn", SPEC, TOPIC, 0.0, "single",
          "Комбинация линейного и логарифмического цикла → O(n log n): типичный middle-вопрос.")
def _nlogn(rng):
    d = rng.choice([2, 3, 4])
    i, j = rng.choice([("i", "j"), ("a", "b"), ("x", "y"), ("k", "m")])
    variant = rng.choice(["nlogn", "logn", "logn_mul", "n_two_loops", "n2half"])
    if variant == "nlogn":
        code, ans = f"for {i} in range(n):\n    {j} = n\n    while {j} > 1:\n        {j} //= {d}", "O(n log n)"
    elif variant == "logn":
        code, ans = f"{j} = n\nwhile {j} > 1:\n    {j} //= {d}\n    total += 1", "O(log n)"
    elif variant == "logn_mul":
        code, ans = f"{j} = 1\nwhile {j} < n:\n    {j} *= {d}\n    total += 1", "O(log n)"
    elif variant == "n_two_loops":
        code, ans = f"for {i} in range(n):\n    total += {i}\nfor {j} in range({d} * n):\n    total -= 1", "O(n)"
    else:
        code, ans = f"for {i} in range(n):\n    for {j} in range({i}):\n        total += 1", "O(n²)"
    return {"text": "Какова временная сложность фрагмента?", "code": code, **choice(rng, ans, rng.sample(BIG_O, len(BIG_O)))}


@template("backend.arch.lru_misses", SPEC, TOPIC, 0.6, "number",
          "Моделирование LRU-кэша по последовательности обращений — нужно держать состояние в голове.")
def _lru(rng):
    cap = rng.randint(2, 3)
    keys = rng.sample(["A", "B", "C", "D", "E"], 4)
    seq = [rng.choice(keys) for _ in range(rng.randint(7, 9))]
    cache, misses = [], 0
    for x in seq:
        if x in cache:
            cache.remove(x)
        else:
            misses += 1
            if len(cache) == cap:
                cache.pop(0)
        cache.append(x)
    return {"text": f"LRU-кэш ёмкостью {cap} элемента, вначале пуст. Обращения по порядку: {', '.join(seq)}. "
                    f"Сколько будет промахов (cache miss)?", "answer": misses}


@template("backend.arch.kafka_partitions", SPEC, TOPIC, 1.0, "number",
          "Группа потребителей Kafka: одна партиция — один потребитель группы; лишние простаивают.")
def _kafka(rng):
    p, c = rng.randint(2, 12), rng.randint(2, 12)
    if rng.random() < 0.5:
        return {"text": f"Топик Kafka из {p} партиций читает одна consumer group из {c} потребителей. "
                        f"Сколько потребителей будут простаивать (без партиций)?", "answer": max(0, c - p)}
    return {"text": f"Топик Kafka из {p} партиций читает одна consumer group из {c} потребителей. "
                    f"Какое максимальное число партиций достанется одному потребителю при равномерном распределении?",
            "answer": -(-p // c)}


@template("backend.arch.little_law", SPEC, TOPIC, 1.5, "number",
          "Закон Литтла L = λ·W для оценки ёмкости пула соединений — senior-уровень.")
def _little(rng):
    lam = rng.randint(2, 40) * 25
    w = rng.randint(2, 40) * 5
    return {"text": f"Сервис стабильно получает {lam} запросов в секунду, среднее время обработки запроса — {w} мс. "
                    f"Сколько запросов в среднем обрабатывается одновременно (сколько соединений нужно пулу)?",
            "answer": lam * w // 1000 if lam * w % 1000 == 0 else round(lam * w / 1000, 1)}
