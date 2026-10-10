"""Модуль matching: подбор кандидатов под потребность работодателя с объяснением (CONTRACT 4, 8.3).

Чистые функции без БД и FastAPI. Не импортирует testing и profile (ADR 0001): оценка ФСП приходит данными
(cand["fsp_score"], cand["fsp_explain"]) или через переданную функцию fsp_fn.
"""
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone

from app.catalog import GRADES, RELEVANCE_MULTIPLIER, RELEVANT_DISCIPLINES, WORK_FORMAT_TITLES

W_STACK, W_TEST, W_FSP, W_FRESH, W_PREF = 0.40, 0.30, 0.15, 0.10, 0.05
UNCONFIRMED_MULT = 0.6
NO_FSP_TEXT = "Нет истории ФСП — оценка только по тесту"


def _pct(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def _now(now):
    now = now or datetime.now(timezone.utc)
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _as_dt(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def stack_match(need_skills: list[dict], cand_skills: list[str]) -> tuple[float, list[str], list[str]]:
    have = {s.lower() for s in cand_skills or []}
    total = sum(float(s.get("weight", 1)) for s in need_skills) or 1.0
    got = [s["name"] for s in need_skills if s["name"].lower() in have]
    miss = [s["name"] for s in need_skills if s["name"].lower() not in have]
    return sum(float(s.get("weight", 1)) for s in need_skills if s["name"].lower() in have) / total, got, miss


def freshness(tested_at, now) -> float:
    """1 при тесте моложе 90 дней, далее линейно до 0,3 к году; без теста — 0."""
    if tested_at is None:
        return 0.0
    days = (now - tested_at).days
    if days <= 90:
        return 1.0
    if days >= 365:
        return 0.3
    return 1.0 - 0.7 * (days - 90) / (365 - 90)


def percentile(theta: float | None, population: list[float]) -> float:
    """Доля кандидатов категории с θ ниже (середина для равных), 0..1."""
    if theta is None or not population:
        return 0.0
    pop = sorted(population)
    lo, hi = bisect_left(pop, theta), bisect_right(pop, theta)
    if len(pop) == 1:
        return 1.0
    return min(1.0, (lo + (hi - lo - 1) / 2) / (len(pop) - 1))


def _fallback_fsp(results: list[dict], spec: str) -> tuple[float, list[dict]]:
    # Используется, только если вызывающий не передал fsp_score/fsp_fn. Формула совпадает с profile.fsp_score.
    if not results:
        return 0.0, [{"factor": "fsp", "text": NO_FSP_TEXT}]
    pts = {"winner": 1.0, "prize": 0.7, "participant": 0.2}
    rel = RELEVANT_DISCIPLINES.get(spec, set())
    s = sum(pts.get(r["role"], 0) * (RELEVANCE_MULTIPLIER if r["discipline"] in rel else 1.0) for r in results)
    return min(1.0, s / 3.0), [{"factor": "fsp", "text": f"Подтверждённых результатов ФСП: {len(results)}"}]


def score(need: dict, cand: dict, now=None) -> tuple[float, list[dict]]:
    """Скор 0..100 и объяснение. cand = поля candidates.json + {grade, status, theta, tested_at}
    и, если есть, {theta_pct, fsp_score, fsp_explain}."""
    now = _now(now)
    explain: list[dict] = []

    sm, got, miss = stack_match(need.get("skills", []), cand.get("skills", []))
    text = f"Стек: совпало {len(got)} из {len(got) + len(miss)}"
    if got:
        text += f" ({', '.join(got)})"
    if miss:
        text += f"; нет: {', '.join(miss)}"
    explain.append({"factor": "stack", "weight": W_STACK, "value": round(sm, 3), "text": text})

    theta, status, grade = cand.get("theta"), cand.get("status"), cand.get("grade")
    ts = cand.get("theta_pct")
    if ts is None:
        ts = 0.0 if theta is None else (max(-3.0, min(3.0, theta)) + 3) / 6
    if theta is None:
        t_text = "Тест не пройден"
    elif status == "confirmed":
        t_text = f"Подтвердил {grade}: θ = {_pct(theta)}, лучше {round(ts * 100)} % категории"
    else:
        t_text = f"Тест на {grade} пройден ниже порога: θ = {_pct(theta)}, лучше {round(ts * 100)} % категории"
    explain.append({"factor": "test", "weight": W_TEST, "value": round(ts, 3), "text": t_text})

    if "fsp_score" in cand:
        fs, fx = cand["fsp_score"], cand.get("fsp_explain") or []
    else:
        fs, fx = _fallback_fsp(cand.get("results", []), need.get("spec", cand.get("spec")))
    fsp_text = "; ".join(e["text"] for e in fx) or (NO_FSP_TEXT if fs == 0 else "")
    explain.append({"factor": "fsp", "weight": W_FSP, "value": round(fs, 3), "text": fsp_text})

    tested = _as_dt(cand.get("tested_at"))
    fr = freshness(tested, now)
    if tested is None:
        f_text = "Нет данных о тесте"
    else:
        days = max(0, (now - tested).days)
        f_text = f"Тест пройден {days} дн. назад" + (" — профиль актуален" if fr == 1.0 else "")
    explain.append({"factor": "freshness", "weight": W_FRESH, "value": round(fr, 3), "text": f_text})

    pm, p_texts = 0.0, []
    need_fmt, cand_fmt = need.get("work_format"), cand.get("work_format")
    if need_fmt and cand_fmt:
        if need_fmt == cand_fmt:
            pm += 0.5
            p_texts.append(f"формат совпадает ({WORK_FORMAT_TITLES.get(need_fmt, need_fmt)})")
        elif "hybrid" in (need_fmt, cand_fmt):
            pm += 0.25
            p_texts.append(f"формат частично совпадает ({WORK_FORMAT_TITLES.get(cand_fmt, cand_fmt)})")
        else:
            p_texts.append(f"формат другой ({WORK_FORMAT_TITLES.get(cand_fmt, cand_fmt)})")
    exp_from, sal_to = cand.get("salary_expect_from"), need.get("salary_to")
    if exp_from is not None and sal_to is not None:
        if exp_from <= sal_to:
            pm += 0.5
            p_texts.append("ожидания по зарплате в вилке")
        else:
            p_texts.append(f"ожидания по зарплате выше вилки ({exp_from:,} ₽)".replace(",", " "))
    explain.append({"factor": "preferences", "weight": W_PREF, "value": round(pm, 3),
                    "text": "Условия: " + ("; ".join(p_texts) if p_texts else "нет данных")})

    total = 100 * (W_STACK * sm + W_TEST * ts + W_FSP * fs + W_FRESH * fr + W_PREF * pm)
    if status != "confirmed":
        total *= UNCONFIRMED_MULT
        explain.append({"factor": "unconfirmed", "weight": UNCONFIRMED_MULT, "value": UNCONFIRMED_MULT,
                        "text": f"Грейд {grade or '—'} не подтверждён тестом — скор × 0,6"})
    return round(total, 2), explain


def _grade_ok(cand_grade, need_grade, grade_adj: bool) -> bool:
    if cand_grade not in GRADES or need_grade not in GRADES:
        return False
    return abs(GRADES.index(cand_grade) - GRADES.index(need_grade)) <= (1 if grade_adj else 0)


def rank(need: dict, cands: list[dict], grade_adj: bool = False, fsp_only: bool = False,
         extra_skills: list[str] | None = None, limit: int = 50, now=None, fsp_fn=None) -> list[dict]:
    """Жёсткий фильтр по категории (специализация + грейд, опционально соседние грейды), затем ранжирование.
    extra_skills — уточнение: кандидат обязан иметь все эти навыки. → [{candidate_id, score, explain}]."""
    now = _now(now)
    extra = {s.lower() for s in extra_skills or []}
    pool = []
    for c in cands:
        if c.get("spec") != need.get("spec") or c.get("grade") is None:
            continue
        if not _grade_ok(c.get("grade"), need.get("grade"), grade_adj):
            continue
        if fsp_only and not c.get("results"):
            continue
        if extra and not extra <= {s.lower() for s in c.get("skills", [])}:
            continue
        pool.append(c)

    # процентиль θ внутри категории кандидата (спец + грейд), по всем переданным кандидатам
    pops: dict[tuple, list[float]] = {}
    for c in cands:
        if c.get("theta") is not None and c.get("grade"):
            pops.setdefault((c.get("spec"), c.get("grade")), []).append(c["theta"])

    out = []
    for c in pool:
        c = dict(c)
        if c.get("theta_pct") is None:
            c["theta_pct"] = percentile(c.get("theta"), pops.get((c.get("spec"), c.get("grade")), []))
        if "fsp_score" not in c and fsp_fn is not None:
            c["fsp_score"], c["fsp_explain"] = fsp_fn(c.get("results", []), need["spec"])
        s, ex = score(need, c, now)
        out.append({"candidate_id": c["id"], "score": s, "explain": ex})
    out.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    return out[:limit]


def keyword_baseline(need: dict, cands: list[dict], limit: int = 50) -> list[dict]:
    """Базовая линия «поиск по резюме»: совпадение навыков + заявленный грейд, без теста и ФСП."""
    out = []
    for c in cands:
        if c.get("spec") != need.get("spec"):
            continue
        have = {s.lower() for s in c.get("skills", [])}
        s = sum(float(sk.get("weight", 1)) for sk in need.get("skills", []) if sk["name"].lower() in have)
        s += 2 * (c.get("claimed_grade") == need.get("grade"))
        out.append({"candidate_id": c["id"], "score": round(s + (c.get("experience_years") or 0) / 100, 4),
                    "explain": [{"factor": "keywords", "text": "Совпадение ключевых слов резюме"}]})
    out.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    return out[:limit]


def category_counts(need: dict, cands: list[dict]) -> list[dict]:
    """Подходящие категории для потребности с числом кандидатов: целевой грейд и соседние."""
    out = []
    for g in GRADES:
        if not _grade_ok(g, need.get("grade"), True):
            continue
        same = [c for c in cands if c.get("spec") == need.get("spec") and c.get("grade") == g]
        out.append({"spec": need["spec"], "grade": g, "target": g == need.get("grade"),
                    "total": len(same), "confirmed": sum(1 for c in same if c.get("status") == "confirmed"),
                    "with_fsp": sum(1 for c in same if c.get("results"))})
    return out
