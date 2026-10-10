"""frontend / css — семантика HTML, блочная модель, специфичность, flex, схлопывание отступов, доступность."""
from app.bank._base import template, choice

SPEC, TOPIC = "frontend", "css"


@template("frontend.css.semantic", SPEC, TOPIC, -1.3, "single",
          "Семантические теги HTML — junior.")
def _semantic(rng):
    text, ans = rng.choice([
        ("Блок основной навигации по сайту.", "<nav>"), ("Основное содержимое страницы (один раз на странице).", "<main>"),
        ("Элемент, по нажатию на который отправляется форма.", "<button>"), ("Самостоятельная статья или карточка новости.", "<article>"),
        ("Нижняя часть страницы с контактами.", "<footer>"),
        ("Шапка страницы с логотипом.", "<header>"), ("Боковая колонка со связанными ссылками.", "<aside>"),
        ("Подпись к полю ввода формы.", "<label>"), ("Иллюстрация вместе с подписью к ней.", "<figure>"),
        ("Список шагов инструкции, где важен порядок.", "<ol>"),
    ])
    tags = ["<div>", "<span>", "<section>", "<nav>", "<main>", "<button>", "<header>", "<aside>", "<label>", "<ol>"]
    return {"text": "Какой тег семантически подходит? " + text, **choice(rng, ans, rng.sample(tags, len(tags)))}


@template("frontend.css.box_model", SPEC, TOPIC, -0.5, "number",
          "Блочная модель content-box/border-box — junior/middle.")
def _box(rng):
    w, p, b = rng.randint(10, 40) * 10, rng.randint(1, 4) * 5, rng.randint(1, 5)
    sizing = rng.choice(["content-box", "border-box"])
    total = w + 2 * p + 2 * b if sizing == "content-box" else w
    return {"text": "Какова итоговая ширина блока на экране в пикселях (без margin)?",
            "code": f".card {{\n  box-sizing: {sizing};\n  width: {w}px;\n  padding: {p}px;\n  border: {b}px solid #520978;\n}}",
            "answer": total}


def _spec(sel: str) -> tuple[int, int, int]:
    ids = sel.count("#")
    classes = sel.count(".") + sel.count("[") + sel.count(":") - 2 * sel.count("::")
    tags = sum(1 for part in sel.replace(">", " ").split() if part[0].isalpha())
    return ids, classes, tags


@template("frontend.css.specificity", SPEC, TOPIC, 0.3, "single",
          "Специфичность селекторов (id, классы, теги) — middle.")
def _specificity(rng):
    color = rng.choice(["red", "green", "blue", "orange"])
    pool = ["#menu a", ".nav .item a", "nav a", "ul li a", ".item a", "#menu .item", "a:hover", "nav .item > a",
            "div#menu a", ".nav a.active", "a"]
    while True:
        sels = rng.sample(pool, 4)
        specs = [_spec(s) for s in sels]
        best = max(specs)
        if specs.count(best) == 1:
            break
    ans = sels[specs.index(best)]
    return {"text": f"Все селекторы ниже задают color ссылке, правила идут в случайном порядке, !important нет. "
                    f"Какой селектор победит (все совпадают с элементом)?", **choice(rng, ans, sels)}


@template("frontend.css.flex_grow", SPEC, TOPIC, 0.8, "number",
          "Распределение свободного места по flex-grow — нужно посчитать, а не угадать.")
def _flex(rng):
    while True:
        g = [rng.randint(1, 3) for _ in range(3)]
        basis = rng.choice([50, 100, 120])
        free = rng.choice([120, 180, 240, 360, 480])
        if all(free * x % sum(g) == 0 for x in g):
            break
    width = basis * 3 + free
    k = rng.randint(0, 2)
    return {"text": f"Ширина flex-контейнера {width}px, у трёх элементов flex-basis: {basis}px, flex-shrink и отступы не влияют. "
                    f"Значения flex-grow: {g[0]}, {g[1]}, {g[2]}. Какой будет ширина элемента №{k + 1} в пикселях?",
            "answer": basis + free * g[k] // sum(g)}


@template("frontend.css.margin_collapse", SPEC, TOPIC, 1.1, "number",
          "Схлопывание вертикальных margin соседних блоков — частая неожиданность.")
def _collapse(rng):
    m1, m2 = rng.randint(2, 64), rng.randint(2, 64)
    return {"text": "Два соседних блочных элемента в обычном потоке (не flex и не grid). Какое расстояние в пикселях будет между ними по вертикали?",
            "code": f".first  {{ margin-bottom: {m1}px; }}\n.second {{ margin-top: {m2}px; }}", "answer": max(m1, m2)}


@template("frontend.css.a11y", SPEC, TOPIC, 1.5, "single",
          "Доступность (WCAG, ARIA) — знания уровня senior.")
def _a11y(rng):
    text, ans, wrong = rng.choice([
        ("Минимальный коэффициент контраста обычного текста к фону по WCAG 2.1, уровень AA?",
         "4.5:1", ["3:1", "2:1", "7:1"]),
        ("Кнопка содержит только svg-иконку корзины. Как дать ей доступное имя для скринридера?",
         'aria-label="Удалить"', ['title у svg без role', 'alt="Удалить" у button', 'tabindex="-1"']),
        ("Картинка чисто декоративная. Какой alt правильный?",
         'alt=""', ['alt="image"', "атрибут alt не указывать", 'alt="декоративная картинка"']),
        ("Чем лучше всего сделать кликабельный элемент, доступный с клавиатуры без доп. кода?",
         "<button>", ['<div onclick>', '<span role="link">', '<a> без href']),
        ("Минимальный коэффициент контраста крупного текста (от 18pt или от 14pt жирным) по WCAG 2.1, уровень AA?",
         "3:1", ["4.5:1", "7:1", "2:1"]),
        ("Как связать подпись с полем ввода, чтобы скринридер прочитал её при фокусе на поле?",
         '<label for="email"> и id="email" у input', ["только placeholder", "<span> рядом с полем", "title у тега form"]),
        ("Какой ARIA-атрибут сообщает, что раскрывающийся блок сейчас открыт?",
         'aria-expanded="true"', ['aria-hidden="false"', 'aria-pressed="true"', 'aria-live="polite"']),
        ("Как сообщить скринридеру о появившемся сообщении «Сохранено», не перемещая фокус?",
         'контейнер с aria-live="polite"', ["aria-label у кнопки «Сохранить»", 'tabindex="0" у сообщения', 'role="presentation"']),
    ])
    return {"text": text, **choice(rng, ans, wrong)}
