"""frontend / react — хуки, батчинг обновлений состояния, эффекты, редьюсеры."""
from app.bank._base import template, choice

SPEC, TOPIC = "frontend", "react"


@template("frontend.react.which_hook", SPEC, TOPIC, -1.2, "single",
          "Назначение базовых хуков — junior.")
def _which_hook(rng):
    text, ans = rng.choice([
        ("Нужно хранить значение счётчика и перерисовывать компонент при его изменении.", "useState"),
        ("Нужно подписаться на событие окна после монтирования и отписаться при размонтировании.", "useEffect"),
        ("Нужно получить доступ к DOM-элементу input, чтобы поставить на него фокус.", "useRef"),
        ("Нужно не пересчитывать дорогое вычисление при каждом рендере, пока не изменились входные данные.", "useMemo"),
        ("Нужно прочитать текущую тему оформления из контекста, не прокидывая её через props.", "useContext"),
        ("Нужно сохранить одну и ту же функцию-обработчик между рендерами для мемоизированного дочернего компонента.", "useCallback"),
        ("Состояние со многими действиями (add, remove, reset) удобнее описать функцией-редьюсером.", "useReducer"),
        ("Нужно хранить значение между рендерами, но его изменение не должно вызывать перерисовку.", "useRef"),
    ])
    hooks = ["useState", "useEffect", "useRef", "useMemo", "useContext", "useCallback", "useReducer"]
    return {"text": "Какой хук React подходит? " + text, **choice(rng, ans, rng.sample(hooks, len(hooks)))}


@template("frontend.react.basics", SPEC, TOPIC, -0.6, "single",
          "Ключи списков, неизменяемость props, условный рендер — базовые правила React.")
def _basics(rng):
    text, ans, wrong = rng.choice([
        ("Что нужно передать каждому элементу при рендере списка через map, чтобы React корректно сопоставлял элементы?",
         "уникальный key", ["уникальный id в style", "ref", "индекс в className"]),
        ("Компонент получил props.title. Как правильно изменить заголовок?",
         "родитель передаёт новое значение props", ["присвоить props.title = '...'", "вызвать this.forceUpdate()", "изменить DOM напрямую"]),
        ("Что вернёт компонент, чтобы ничего не отрисовать?",
         "null", ["undefined", "false в виде строки", "пустой объект {}"]),
        ("Можно ли вызывать useState внутри условия if?",
         "нет: хуки вызываются на верхнем уровне компонента, всегда в одном порядке",
         ["да, если условие не меняется между рендерами", "да, в любом месте функции", "только в классовых компонентах"]),
        ("Как правильно добавить элемент x в массив items, который хранится в состоянии?",
         "setItems([...items, x])", ["items.push(x)", "items.push(x); setItems(items)", "items[items.length] = x"]),
        ("Что делает <>...</> (React.Fragment)?",
         "группирует элементы без лишнего узла в DOM", ["лениво загружает компонент", "передаёт контекст вниз по дереву",
                                                        "мемоизирует дочерние элементы"]),
        ("Как дочернему компоненту передать данные родителю?",
         "родитель передаёт функцию-колбэк в props, ребёнок её вызывает",
         ["ребёнок присваивает значение в props родителя", "через ref на родительский компонент", "никак, данные идут только вниз"]),
        ("Что такое управляемый (controlled) input?",
         "значение хранится в состоянии React и задаётся через value + onChange",
         ["input с атрибутом name", "input, который рендерится только на сервере", "input без обработчика onChange"]),
    ])
    return {"text": text, **choice(rng, ans, wrong)}


@template("frontend.react.batching", SPEC, TOPIC, 0.2, "number",
          "setState с устаревшим значением в одном обработчике: обновления батчатся — частая ошибка middle.")
def _batching(rng):
    start, a, m = rng.randint(0, 20), rng.randint(1, 9), rng.randint(2, 5)
    s = rng.choice(["count", "clicks", "total", "score", "value"])
    setter = "set" + s[0].upper() + s[1:]
    body = "\n".join(f"    {setter}({s} + {a});" for _ in range(m))
    return {"text": f"{s} изначально равен {start}. Чему будет равен {s} после одного клика?",
            "code": f"const [{s}, {setter}] = useState({start});\nfunction onClick() {{\n{body}\n}}",
            "answer": start + a}


@template("frontend.react.functional_update", SPEC, TOPIC, 0.7, "number",
          "Смесь обычных и функциональных обновлений состояния — нужно понимать очередь обновлений.")
def _functional(rng):
    start = rng.randint(0, 5)
    ops = []
    for _ in range(rng.randint(3, 4)):
        ops.append((rng.choice(["value", "fn"]), rng.randint(1, 5)))
    val, lines = start, []
    for kind, x in ops:
        if kind == "value":
            val = start + x
            lines.append(f"    setCount(count + {x});")
        else:
            val = val + x
            lines.append(f"    setCount(c => c + {x});")
    return {"text": f"count изначально равен {start}. Чему будет равен count после одного клика?",
            "code": f"const [count, setCount] = useState({start});\nfunction onClick() {{\n" + "\n".join(lines) + "\n}",
            "answer": val}


@template("frontend.react.effect_runs", SPEC, TOPIC, 1.0, "number",
          "Сколько раз сработает useEffect при заданных зависимостях — понимание сравнения deps.")
def _effect_runs(rng):
    vals = [rng.randint(1, 3) for _ in range(rng.randint(4, 6))]
    deps = rng.choice(["[id]", "[]", "none"])
    if deps == "[id]":
        runs = 1 + sum(1 for a, b in zip(vals, vals[1:]) if a != b)
    elif deps == "[]":
        runs = 1
    else:
        runs = len(vals)
    dep_code = "" if deps == "none" else f", {deps}"
    return {"text": (f"Компонент отрисовался {len(vals)} раз подряд (без размонтирования); значения пропа id на рендерах: "
                     f"{', '.join(map(str, vals))}. Сколько раз выполнится тело эффекта? (StrictMode выключен)"),
            "code": f"function Card({{ id }}) {{\n  useEffect(() => {{\n    load(id);\n  }}{dep_code});\n  return <div />;\n}}",
            "answer": runs}


@template("frontend.react.reducer", SPEC, TOPIC, 1.4, "number",
          "Состояние после серии dispatch в редьюсере списка задач — нужно аккуратно проследить состояние.")
def _reducer(rng):
    todos, nxt, actions = [], 1, []
    for _ in range(rng.randint(5, 7)):
        kind = rng.choice(["add", "add", "toggle", "remove"]) if todos else "add"
        if kind == "add":
            actions.append(f"dispatch({{ type: 'add', id: {nxt} }});")
            todos.append({"id": nxt, "done": False})
            nxt += 1
        else:
            t = rng.choice(todos)
            actions.append(f"dispatch({{ type: '{kind}', id: {t['id']} }});")
            if kind == "toggle":
                t["done"] = not t["done"]
            else:
                todos.remove(t)
    code = ("function reducer(state, a) {\n  switch (a.type) {\n"
            "    case 'add': return [...state, { id: a.id, done: false }];\n"
            "    case 'toggle': return state.map(t => t.id === a.id ? { ...t, done: !t.done } : t);\n"
            "    case 'remove': return state.filter(t => t.id !== a.id);\n"
            "    default: return state;\n  }\n}\n// начальное состояние: []\n" + "\n".join(actions))
    if rng.random() < 0.5:
        return {"text": "Сколько задач с done === true будет в состоянии после всех dispatch?", "code": code,
                "answer": sum(t["done"] for t in todos)}
    return {"text": "Сколько задач будет в состоянии после всех dispatch?", "code": code, "answer": len(todos)}
