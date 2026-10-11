"""Модуль testing: банк шаблонов, адаптивная сборка теста, оценка θ по Раша, грейд, кулдаун (CONTRACT 3, 8.3).

Чистые функции без БД и FastAPI: состояние попытки — обычный dict, его хранит вызывающий код.
Не импортирует profile и matching.
"""
import hashlib
import math
import random
from datetime import datetime, timedelta

from app.bank import REGISTRY as _REGISTRY
from app.bank._base import Template
from app.catalog import GRADES, THRESHOLDS

TEMPLATES: dict[str, Template] = {tid: t for tid, t in _REGISTRY.items() if t.enabled}

N_ITEMS = 10            # экспресс-тест: 10 заданий за 5 минут
WARMUP = 3              # первые 3 задания — около порога заявленного грейда
STEP = 0.6              # шаг адаптации сложности после разминки
NEAR = 0.35             # «около цели»: случайный выбор среди шаблонов с |b − цель| ≤ лучший + NEAR
PRIOR_SD = 3.0          # очень слабая регуляризация ОМП: конечная оценка при всех верных/неверных


def variant_seed(candidate_id, attempt_no, template_id) -> int:
    """Сид варианта: sha256(candidate:attempt:template) — у каждого кандидата и попытки свои числа."""
    return int(hashlib.sha256(f"{candidate_id}:{attempt_no}:{template_id}".encode()).hexdigest()[:16], 16)


def variant_hash(item: dict) -> str:
    """Отпечаток содержимого варианта — для проверки уникальности (валидация утечки)."""
    payload = f"{item['text']}|{item.get('code')}|{item.get('options')}|{item['answer']}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def topics_for(spec: str) -> list[str]:
    return sorted({t.topic for t in TEMPLATES.values() if t.spec == spec})


def has_bank(spec: str) -> bool:
    return len([t for t in TEMPLATES.values() if t.spec == spec]) >= N_ITEMS


# ---------------------------------------------------------------- попытка

def build_attempt(candidate_id: int, spec: str, claimed_grade: str, attempt_no: int) -> dict:
    """Новое состояние попытки. Темы идут по кругу в порядке, зависящем от кандидата и попытки."""
    if claimed_grade not in THRESHOLDS:
        raise ValueError(f"unknown grade {claimed_grade}")
    topics = topics_for(spec)
    if not topics:
        raise ValueError(f"no templates for spec {spec}")
    rng = random.Random(variant_seed(candidate_id, attempt_no, "topics"))
    rng.shuffle(topics)
    return {
        "candidate_id": candidate_id, "spec": spec, "claimed_grade": claimed_grade, "attempt_no": attempt_no,
        "topics": topics, "target": THRESHOLDS[claimed_grade], "n_items": N_ITEMS,
        "used": [], "responses": [], "current": None,
    }


def _pick_template(state: dict) -> Template:
    k = len(state["responses"])
    topic = state["topics"][k % len(state["topics"])]
    pool = [t for t in TEMPLATES.values()
            if t.spec == state["spec"] and t.id not in state["used"]]
    by_topic = [t for t in pool if t.topic == topic] or pool
    target = state["target"]
    best = min(abs(t.b - target) for t in by_topic)
    near = sorted((t for t in by_topic if abs(t.b - target) <= best + NEAR), key=lambda t: t.id)
    rng = random.Random(variant_seed(state["candidate_id"], state["attempt_no"], f"pick{k}"))
    return rng.choice(near)


def next_item(state: dict) -> dict | None:
    """Текущее задание (с ответом — только для сервера) или None, если тест окончен."""
    if len(state["responses"]) >= state["n_items"]:
        return None
    if state["current"] is None:
        t = _pick_template(state)
        seed = variant_seed(state["candidate_id"], state["attempt_no"], t.id)
        item = t.generate(seed)
        item["item_id"] = f"{t.id}#{seed % 10**8:08d}"
        item["topic"] = t.topic
        item["b"] = t.b
        item["no"] = len(state["responses"]) + 1
        state["current"] = item
        state["used"].append(t.id)
    return state["current"]


def public_item(item: dict | None, state: dict | None = None) -> dict | None:
    """Задание для кандидата: без ответа и без b."""
    if item is None:
        return None
    out = {k: item[k] for k in ("item_id", "template_id", "text", "code", "kind", "options", "topic", "no")}
    out["total"] = state["n_items"] if state else N_ITEMS
    return out


def check_answer(item: dict, answer) -> bool:
    kind, correct = item["kind"], item["answer"]
    try:
        if kind == "single":
            opts = item["options"] or []
            if isinstance(answer, int) and not isinstance(answer, bool) and 0 <= answer < len(opts):
                answer = opts[answer]
            return str(answer).strip() == str(correct)
        if kind == "number":
            got = float(str(answer).replace(",", ".").replace(" ", ""))
            return math.isclose(got, float(correct), rel_tol=1e-6, abs_tol=1e-6)
        if kind == "order":
            opts = item["options"] or []
            seq = [opts[a] if isinstance(a, int) and not isinstance(a, bool) else str(a) for a in answer]
            return seq == list(correct)
    except (TypeError, ValueError, IndexError):
        return False
    return False


def submit(state: dict, item_id: str, answer, late: bool = False) -> bool:
    """Принять ответ на текущее задание. late=True — превышен лимит времени на задание (засчитывается неверным)."""
    item = state["current"]
    if item is None or item["item_id"] != item_id:
        raise ValueError("item is not current")
    correct = (not late) and check_answer(item, answer)
    state["responses"].append({"template_id": item["template_id"], "item_id": item_id, "b": item["b"],
                               "correct": correct, "variant_hash": variant_hash(item), "late": late})
    state["current"] = None
    if len(state["responses"]) >= WARMUP:          # после разминки: верно — сложнее, неверно — проще
        state["target"] = max(-3.0, min(3.0, state["target"] + (STEP if correct else -STEP)))
    return correct


def estimate_theta(responses: list[tuple[float, bool]]) -> float:
    """θ по модели Раша: максимум правдоподобия на сетке [−3; 3] с шагом 0,01.

    Слабая регуляризация N(0, 3²) почти не влияет на оценку, но при всех верных (неверных) ответах
    даёт конечное значение у границы со сдвигом к центру; оценка монотонна по числу верных ответов.
    """
    if not responses:
        return 0.0
    best_t, best_ll = 0.0, -math.inf
    for i in range(-300, 301):
        t = i / 100
        ll = -t * t / (2 * PRIOR_SD ** 2)
        for b, ok in responses:
            z = t - b
            ll += -math.log1p(math.exp(-z)) if ok else -math.log1p(math.exp(z))
        if ll > best_ll:
            best_t, best_ll = t, ll
    return best_t


def grade_from_theta(theta: float) -> str | None:
    grade = None
    for g in GRADES:
        if theta >= THRESHOLDS[g]:
            grade = g
    return grade


def finish(state: dict) -> dict:
    """Итог попытки: θ, подтверждён ли заявленный грейд, предложение повыситься, разбор по темам.

    Брошенная попытка (время вышло): выданное, но неотвеченное задание засчитывается неверным как обычное, а каждое
    невыданное — неверным ответом на задание сложности порога заявленного грейда. Иначе выход после пары верных
    ответов давал бы высокий θ, а пустая попытка — θ = 0 и подтверждённый Junior. В разбор по темам и items идут
    только реально выданные задания; невыданные — в счётчике unanswered.
    """
    item = state.get("current")
    if item is not None and len(state["responses"]) < state["n_items"]:
        submit(state, item["item_id"], None, late=True)
        state["responses"][-1]["unanswered"] = True
    resp = state["responses"]
    claimed = state["claimed_grade"]
    not_reached = max(0, state["n_items"] - len(resp))
    theta = round(estimate_theta([(r["b"], r["correct"]) for r in resp]
                                 + [(THRESHOLDS[claimed], False)] * not_reached), 2)
    confirmed = theta >= THRESHOLDS[claimed]
    gi = GRADES.index(claimed)
    suggest_upgrade = confirmed and gi + 1 < len(GRADES) and theta >= THRESHOLDS[GRADES[gi + 1]]
    by_topic: dict[str, dict] = {}
    for r in resp:
        topic = TEMPLATES[r["template_id"]].topic if r["template_id"] in TEMPLATES else "?"
        d = by_topic.setdefault(topic, {"topic": topic, "total": 0, "correct": 0})
        d["total"] += 1
        d["correct"] += int(r["correct"])
    return {"theta": theta, "grade": grade_from_theta(theta), "claimed_grade": claimed, "confirmed": confirmed,
            "suggest_upgrade": suggest_upgrade, "correct": sum(r["correct"] for r in resp),
            "total": len(resp) + not_reached,
            "unanswered": sum(bool(r.get("unanswered")) for r in resp) + not_reached,
            "topics": list(by_topic.values()),
            "items": [{k: r[k] for k in ("template_id", "b", "correct", "variant_hash")} for r in resp]}


def simulate_attempt(candidate_id: int, spec: str, claimed_grade: str, theta_true: float,
                     attempt_no: int, rng_seed: int) -> dict:
    """Прогон настоящего теста «виртуальным кандидатом»: ответ верен с вероятностью 1/(1+exp(−(θ_true − b)))."""
    rng = random.Random(rng_seed)
    state = build_attempt(candidate_id, spec, claimed_grade, attempt_no)
    while (item := next_item(state)) is not None:
        ok = rng.random() < 1 / (1 + math.exp(-(theta_true - item["b"])))
        submit(state, item["item_id"], item["answer"] if ok else _wrong(item))
    res = finish(state)
    return {"theta": res["theta"], "grade": res["grade"], "confirmed": res["confirmed"], "items": res["items"]}


def _wrong(item: dict):
    if item["kind"] == "single":
        return next((o for o in item["options"] if o != item["answer"]), "__wrong__")
    if item["kind"] == "number":
        return float(item["answer"]) + 1
    return list(reversed(item["answer"]))


# ---------------------------------------------------------------- кулдаун

def cooldown_until(last: dict | None, claimed_grade: str, cooldown: timedelta) -> datetime | None:
    """Когда можно начать тест на claimed_grade (None — можно сейчас).

    last = {claimed_grade, result: confirmed|failed, finished_at} — последняя завершённая попытка по специализации.
    Тест на тот же или более высокий грейд — не раньше чем через cooldown; на грейд ниже после провала — сразу.
    """
    if not last or not last.get("finished_at"):
        return None
    lower = GRADES.index(claimed_grade) < GRADES.index(last["claimed_grade"])
    if last.get("result") == "failed" and lower:
        return None
    return last["finished_at"] + cooldown
