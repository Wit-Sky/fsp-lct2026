"""Validation of testing and matching (TEAM: Anton). Run from repo root:  python -X utf8 validation/run_all.py

Writes validation/results.md, validation/results.json and PNG charts to validation/img/.
Uses the real core from backend/app/services if importable, otherwise validation/_stub.py (marked in the report).
"""
import json
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "validation"
IMG = OUT / "img"
IMG.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "backend"))
try:
    from app.services import testing, matching  # noqa: E402
    CORE = "real (backend/app/services)"
except Exception as e:  # noqa: BLE001
    sys.path.insert(0, str(OUT))
    import _stub  # noqa: E402
    testing, matching = _stub.testing, _stub.matching
    CORE = f"STUB (validation/_stub.py) — backend core not importable: {type(e).__name__}: {e}"

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
PURPLE, PINK, GREY = "#520978", "#FF0053", "#8A83D1"
GRADES = ["junior", "middle", "senior"]
THRESHOLDS = {"junior": -0.5, "middle": 0.5, "senior": 1.5}
NOW = datetime(2026, 10, 11)


def grade_by_theta(t):
    g = None
    for name in GRADES:
        if t >= THRESHOLDS[name]:
            g = name
    return g


def gname(g):
    return g or "ниже junior"


def tattr(t, key):
    return t[key] if isinstance(t, dict) else getattr(t, key)


def pearson(x, y):
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else float("nan")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


cands = load("candidates.json")
needs = load("needs.json")
truth = {int(n): {int(c): v for c, v in d.items()} for n, d in load("pairs_labeled.json").items()}
stasya_path = DATA / "pairs_labeled_stasya.json"
stasya = ({int(n): {int(c): v for c, v in d.items()} for n, d in json.loads(stasya_path.read_text(encoding="utf-8")).items()}
          if stasya_path.exists() else None)
cards = load("stasya_cards.json") if (DATA / "stasya_cards.json").exists() else []
R = {"core": CORE}
md = []

# ---------------- A1. test-retest ----------------
att = {}
for c in cands:
    for no in (1, 2):
        att[(c["id"], no)] = testing.simulate_attempt(c["id"], c["spec"], c["claimed_grade"], c["theta_true"], no,
                                                      rng_seed=1000 * no + c["id"])
t1 = [att[(c["id"], 1)]["theta"] for c in cands]
t2 = [att[(c["id"], 2)]["theta"] for c in cands]
same_grade = statistics.fmean(att[(c["id"], 1)]["grade"] == att[(c["id"], 2)]["grade"] for c in cands)
same_conf = statistics.fmean(att[(c["id"], 1)]["confirmed"] == att[(c["id"], 2)]["confirmed"] for c in cands)
r12 = pearson(t1, t2)
R["A1"] = {"grade_agreement": same_grade, "confirmed_agreement": same_conf, "pearson_theta": r12}

fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(t1, t2, s=12, color=PURPLE, alpha=0.6)
ax.plot([-3, 3], [-3, 3], color=PINK, lw=1)
ax.set_xlabel("θ, попытка 1"); ax.set_ylabel("θ, попытка 2")
ax.set_title(f"Повторное прохождение: r = {r12:.2f}".replace(".", ","))
fig.tight_layout(); fig.savefig(IMG / "a1_test_retest.png", dpi=150); plt.close(fig)

# ---------------- A2. accuracy vs truth ----------------
labels = [None] + GRADES
conf = [[0] * 4 for _ in range(4)]
for c in cands:
    a = att[(c["id"], 1)]
    conf[labels.index(grade_by_theta(c["theta_true"]))][labels.index(a["grade"])] += 1
exact = sum(conf[i][i] for i in range(4)) / len(cands)
far = sum(conf[i][j] for i in range(4) for j in range(4) if abs(i - j) > 1) / len(cands)
conf_true = statistics.fmean(a["confirmed"] == ((grade_by_theta(c["theta_true"]) is not None) and
                                                THRESHOLDS[c["claimed_grade"]] <= c["theta_true"])
                             for c in cands for a in [att[(c["id"], 1)]])
mae = statistics.fmean(abs(att[(c["id"], 1)]["theta"] - c["theta_true"]) for c in cands)
R["A2"] = {"exact": exact, "off_by_more_than_one": far, "confirm_decision_correct": conf_true, "mae_theta": mae,
           "matrix": conf}
fig, ax = plt.subplots(figsize=(5.2, 4.4))
ax.imshow(conf, cmap="Purples")
for i in range(4):
    for j in range(4):
        ax.text(j, i, conf[i][j], ha="center", va="center", color="black" if conf[i][j] < 40 else "white")
ax.set_xticks(range(4), [gname(g) for g in labels], rotation=20)
ax.set_yticks(range(4), [gname(g) for g in labels])
ax.set_xlabel("Грейд по тесту"); ax.set_ylabel("Грейд по скрытой правде θ")
ax.set_title("Матрица ошибок грейда")
fig.tight_layout(); fig.savefig(IMG / "a2_confusion.png", dpi=150); plt.close(fig)

# ---------------- A3. discrimination per template ----------------
rows = defaultdict(list)  # template -> [(correct, final_theta, theta_true)]
for (cid, no), a in att.items():
    for it in a["items"]:
        rows[it["template_id"]].append((it["correct"], a["theta"], next_theta := None))
tt = {c["id"]: c["theta_true"] for c in cands}
rows = defaultdict(list)
for (cid, no), a in att.items():
    for it in a["items"]:
        rows[it["template_id"]].append((1 if it["correct"] else 0, a["theta"], tt[cid]))


def b_mle(obs):
    """Refined difficulty b given candidate abilities (final theta), Rasch, clipped [-4; 4]."""
    b = 0.0
    for _ in range(50):
        p = [1 / (1 + math.exp(-(th - b))) for _, th, _ in obs]
        g = -sum(y - pi for (y, _, _), pi in zip(obs, p))
        h = -sum(pi * (1 - pi) for pi in p)
        if abs(h) < 1e-9:
            break
        step = g / h
        b = max(-4, min(4, b - step))
        if abs(step) < 1e-6:
            break
    return b


tmpl_rows = []
for tid, obs in sorted(rows.items()):
    if len(obs) < 10:
        continue
    y = [o[0] for o in obs]; th = [o[1] for o in obs]
    rpb = pearson(y, th) if 0 < sum(y) < len(y) else float("nan")
    srt = sorted(obs, key=lambda o: o[1]); k = len(srt) // 3
    low = statistics.fmean(o[0] for o in srt[:k]) if k else float("nan")
    high = statistics.fmean(o[0] for o in srt[-k:]) if k else float("nan")
    b_decl = tattr(testing.TEMPLATES[tid], "b")
    tmpl_rows.append({"template": tid, "n": len(obs), "rpb": rpb, "p_low": low, "p_high": high,
                      "b_declared": b_decl, "b_refined": b_mle(obs)})
weak = [t for t in tmpl_rows if not (t["rpb"] >= 0.2)]
R["A3"] = {"templates": len(tmpl_rows), "weak_rpb_lt_0_2": len(weak),
           "median_rpb": statistics.median(t["rpb"] for t in tmpl_rows if not math.isnan(t["rpb"])),
           "corr_b_declared_refined": pearson([t["b_declared"] for t in tmpl_rows], [t["b_refined"] for t in tmpl_rows])}
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist([t["rpb"] for t in tmpl_rows if not math.isnan(t["rpb"])], bins=15, color=PURPLE)
ax.axvline(0.2, color=PINK, ls="--"); ax.set_xlabel("Точечно-бисериальная корреляция с итоговым θ")
ax.set_ylabel("Число шаблонов"); ax.set_title("Разделяющая сила шаблонов")
fig.tight_layout(); fig.savefig(IMG / "a3_discrimination.png", dpi=150); plt.close(fig)

# ---------------- A4. leak resistance ----------------
by_t = defaultdict(list)
for (cid, no), a in att.items():
    if no == 1:
        for it in a["items"]:
            by_t[it["template_id"]].append(it["variant_hash"])
same_pairs = total_pairs = 0
for hs in by_t.values():
    cnt = Counter(hs); n = len(hs)
    total_pairs += n * (n - 1) // 2
    same_pairs += sum(v * (v - 1) // 2 for v in cnt.values())
share_same = same_pairs / total_pairs if total_pairs else 0.0

lrng = random.Random(7)
gains, gains_single = [], []
for c in lrng.sample(cands, 100):
    others = [o for o in cands if o["id"] != c["id"] and o["spec"] == c["spec"]]
    leaked = {it["variant_hash"] for o in lrng.sample(others, min(50, len(others)))
              for it in att[(o["id"], 1)]["items"]}
    honest = att[(c["id"], 1)]
    resp = [(it["b"], it["correct"] or it["variant_hash"] in leaked) for it in honest["items"]]
    gains.append(testing.estimate_theta(resp) - honest["theta"])
    gains_single.append(testing.estimate_theta([(it["b"], True) for it in honest["items"]]) - honest["theta"])
R["A4"] = {"share_same_variant_pairs": share_same, "mean_theta_gain_leak": statistics.fmean(gains),
           "max_theta_gain_leak": max(gains), "share_with_any_gain": statistics.fmean(g > 1e-9 for g in gains),
           "mean_theta_gain_single_test": statistics.fmean(gains_single)}
fig, ax = plt.subplots(figsize=(5.5, 4))
ax.bar(["Наши варианты\n(сид на кандидата)", "Единый тест\nдля всех"],
       [R["A4"]["mean_theta_gain_leak"], R["A4"]["mean_theta_gain_single_test"]], color=[PURPLE, PINK])
ax.set_ylabel("Средний прирост θ от слива ответов 50 кандидатов")
ax.set_title("Устойчивость к утечке заданий")
fig.tight_layout(); fig.savefig(IMG / "a4_leak.png", dpi=150); plt.close(fig)

# ---------------- categories for matching (from simulated attempt 1) ----------------
pool = []
for c in cands:
    a = att[(c["id"], 1)]
    pool.append({**c, "grade": c["claimed_grade"], "status": "confirmed" if a["confirmed"] else "unconfirmed",
                 "theta": a["theta"], "tested_at": NOW})
for p in pool:
    p.pop("theta_true", None)  # matching never sees the hidden truth
by_id = {p["id"]: p for p in pool}


def p_at(ranked, lab, k):
    return sum(1 for r in ranked[:k] if lab.get(r["candidate_id"], 0) > 0) / k


def ndcg(ranked, lab, k=10):
    dcg = sum((2 ** lab.get(r["candidate_id"], 0) - 1) / math.log2(i + 2) for i, r in enumerate(ranked[:k]))
    ideal = sorted(lab.values(), reverse=True)[:k]
    idcg = sum((2 ** v - 1) / math.log2(i + 2) for i, v in enumerate(ideal))
    return dcg / idcg if idcg else float("nan")


def evaluate(ranker, need_list, lab_all, cand_list):
    res = {"P@5": [], "P@10": [], "nDCG@10": [], "hit2@10": []}
    for nd in need_list:
        lab = lab_all.get(nd["id"], {})
        r = ranker(nd, cand_list)
        res["P@5"].append(p_at(r, lab, 5)); res["P@10"].append(p_at(r, lab, 10))
        v = ndcg(r, lab)
        if not math.isnan(v):
            res["nDCG@10"].append(v)
        res["hit2@10"].append(any(lab.get(x["candidate_id"], 0) == 2 for x in r[:10]))
    return {k: statistics.fmean(v) for k, v in res.items()}


ours = lambda nd, cl: matching.rank(nd, cl, limit=50)  # noqa: E731
ours_adj = lambda nd, cl: matching.rank(nd, cl, grade_adj=True, limit=50)  # noqa: E731
base = lambda nd, cl: matching.keyword_baseline(nd, cl, limit=50)  # noqa: E731

# ---------------- B. matching ----------------
R["B"] = {"ours": evaluate(ours, needs, truth, pool), "ours_grade_adj": evaluate(ours_adj, needs, truth, pool),
          "keyword_baseline": evaluate(base, needs, truth, pool)}
fig, ax = plt.subplots(figsize=(6.5, 4))
mets = ["P@5", "P@10", "nDCG@10", "hit2@10"]
xs = range(len(mets))
ax.bar([x - 0.2 for x in xs], [R["B"]["ours"][m] for m in mets], 0.4, color=PURPLE, label="Наш подбор")
ax.bar([x + 0.2 for x in xs], [R["B"]["keyword_baseline"][m] for m in mets], 0.4, color=GREY, label="По ключевым словам")
ax.set_xticks(list(xs), mets); ax.set_ylim(0, 1); ax.legend(); ax.set_title("Качество подбора, 30 потребностей")
fig.tight_layout(); fig.savefig(IMG / "b_matching.png", dpi=150); plt.close(fig)

# no-FSP candidates
share_nofsp_top, share_nofsp_pool, wins, duels, example = [], [], 0, 0, None
true_theta = {c["id"]: c["theta_true"] for c in cands}
for nd in needs:
    r = matching.rank(nd, pool, limit=50)
    lab = truth.get(nd["id"], {})
    top = r[:10]
    if top:
        share_nofsp_top.append(statistics.fmean(not by_id[x["candidate_id"]]["results"] for x in top))
    same = [p for p in pool if p["spec"] == nd["spec"]]
    share_nofsp_pool.append(statistics.fmean(not p["results"] for p in same))
    pos = {x["candidate_id"]: i for i, x in enumerate(r)}
    strong = [cid for cid, v in lab.items() if v == 2 and not by_id[cid]["results"]]
    weak_f = [p["id"] for p in same if lab.get(p["id"], 0) == 0 and p["results"]]
    for a in strong:
        for b in weak_f:
            if a in pos or b in pos:
                duels += 1
                win = pos.get(a, 10 ** 6) < pos.get(b, 10 ** 6)
                wins += win
                if win and example is None and b in pos:
                    example = (nd["id"], a, pos[a] + 1, b, pos[b] + 1)
R["B_nofsp"] = {"share_in_top10": statistics.fmean(share_nofsp_top) if share_nofsp_top else float("nan"),
                "share_in_pool": statistics.fmean(share_nofsp_pool),
                "strong_nofsp_above_weak_fsp": wins / duels if duels else float("nan"), "duels": duels,
                "example": example}

# ---------------- A5. inter-rater agreement ----------------
if stasya and cards:
    a_lab, b_lab = [], []
    for item in cards:
        nid = item["need"]["id"]
        for cc in item["candidates"]:
            a_lab.append(truth.get(nid, {}).get(cc["candidate_id"], 0))
            b_lab.append(stasya.get(nid, {}).get(cc["candidate_id"], 0))
    n = len(a_lab)
    po = sum(x == y for x, y in zip(a_lab, b_lab)) / n
    pe = sum((a_lab.count(k) / n) * (b_lab.count(k) / n) for k in (0, 1, 2))
    kappa = (po - pe) / (1 - pe)
    w = lambda i, j: 1 - (i - j) ** 2 / 4  # noqa: E731
    pow_ = sum(w(x, y) for x, y in zip(a_lab, b_lab)) / n
    pew = sum(w(i, j) * (a_lab.count(i) / n) * (b_lab.count(j) / n) for i in range(3) for j in range(3))
    kappa_w = (pow_ - pew) / (1 - pew)
    card_needs = [nd for nd in needs if nd["id"] in {it["need"]["id"] for it in cards}]
    sub = {it["need"]["id"]: [by_id[cc["candidate_id"]] for cc in it["candidates"]] for it in cards}
    ev = lambda rk, lab: evaluate(lambda nd, _: rk(nd, sub[nd["id"]]), card_needs, lab, None)  # noqa: E731
    R["A5"] = {"pairs": n, "agreement": po, "kappa": kappa, "kappa_quadratic": kappa_w,
               "ours_vs_stasya": ev(ours_adj, stasya), "baseline_vs_stasya": ev(base, stasya),
               "ours_vs_truth_same_pairs": ev(ours_adj, truth)}
else:
    R["A5"] = None

# ---------------- C. performance ----------------
def timing(cl, need):
    ts = []
    for _ in range(20):
        t0 = time.perf_counter(); matching.rank(need, cl, limit=50); ts.append(time.perf_counter() - t0)
    return statistics.median(ts) * 1000


big = [{**p, "id": p["id"] + 1000 * k} for k in range(10) for p in pool]
R["C"] = {"rank_ms_300": timing(pool, needs[0]), "rank_ms_3000": timing(big, needs[0])}

# ---------------- report ----------------
f = lambda x, d=2: ("—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}".replace(".", ","))  # noqa: E731
pc = lambda x: f(100 * x, 1) + " %"  # noqa: E731
md += [f"# Результаты валидации", "", f"Ядро: **{CORE}**", f"Сгенерировано: `python -X utf8 validation/run_all.py`, данные seed = 42, 300 кандидатов, 30 потребностей.", ""]
md += ["## A. Тестирование", "", "### A1. Повторное прохождение (test-retest)", "",
       f"- Совпадение грейда по тесту между двумя попытками (разные варианты заданий): **{pc(R['A1']['grade_agreement'])}**",
       f"- Совпадение решения «подтверждён / не подтверждён»: **{pc(R['A1']['confirmed_agreement'])}**",
       f"- Корреляция Пирсона θ₁ и θ₂: **{f(R['A1']['pearson_theta'])}**", "", "![](img/a1_test_retest.png)", "",
       "### A2. Точность против скрытой правды", "",
       f"- Точное совпадение грейда: **{pc(R['A2']['exact'])}**; ошибка больше чем на ступень: **{pc(R['A2']['off_by_more_than_one'])}**",
       f"- Решение о подтверждении заявленного грейда верно: **{pc(R['A2']['confirm_decision_correct'])}**",
       f"- Средняя абсолютная ошибка θ: **{f(R['A2']['mae_theta'])}**", "", "![](img/a2_confusion.png)", "",
       "### A3. Разделяющая сила шаблонов", "",
       f"- Шаблонов с ≥ 10 ответами: {R['A3']['templates']}; медиана точечно-бисериальной корреляции: **{f(R['A3']['median_rpb'])}**",
       f"- Корреляция заявленной и уточнённой сложности b: **{f(R['A3']['corr_b_declared_refined'])}**",
       f"- На доработку (корреляция < 0,2): **{R['A3']['weak_rpb_lt_0_2']}**", "", "![](img/a3_discrimination.png)", ""]
md += ["| Шаблон | Ответов | r_pb | Доля верных, нижняя треть | Верхняя треть | b заявл. | b уточн. |", "|---|---|---|---|---|---|---|"]
md += [f"| {t['template']} | {t['n']} | {f(t['rpb'])} | {f(t['p_low'])} | {f(t['p_high'])} | {f(t['b_declared'])} | {f(t['b_refined'])} |"
       for t in sorted(tmpl_rows, key=lambda t: (t["rpb"] if not math.isnan(t["rpb"]) else -9))[:15]]
md += ["", "_Показаны 15 шаблонов с наименьшей корреляцией; полный список — `results.json`._", "",
       "### A4. Устойчивость к утечке", "",
       f"- Доля пар кандидатов с одинаковым вариантом на одном шаблоне: **{pc(R['A4']['share_same_variant_pairs'])}**",
       f"- Слив ответов 50 других кандидатов: средний прирост θ **{f(R['A4']['mean_theta_gain_leak'], 3)}**, максимум {f(R['A4']['max_theta_gain_leak'], 2)}, "
       f"прирост хоть какой-то у {pc(R['A4']['share_with_any_gain'])} из 100 «сливщиков»",
       f"- Для сравнения, единый тест для всех: средний прирост θ **{f(R['A4']['mean_theta_gain_single_test'])}**", "", "![](img/a4_leak.png)", ""]
md += ["### A5. Согласие разметчиков", ""]
if R["A5"]:
    a5 = R["A5"]
    md += [f"- Пар: {a5['pairs']}; совпадение: **{pc(a5['agreement'])}**; каппа Коэна: **{f(a5['kappa'])}**; квадратично-взвешенная каппа: **{f(a5['kappa_quadratic'])}**", "",
           "| На 10 потребностях × 20 карточек | P@5 | P@10 | nDCG@10 |", "|---|---|---|---|",
           f"| Наш подбор (соседние грейды) против независимой разметки | {f(a5['ours_vs_stasya']['P@5'])} | {f(a5['ours_vs_stasya']['P@10'])} | {f(a5['ours_vs_stasya']['nDCG@10'])} |",
           f"| Ключевые слова против независимой разметки | {f(a5['baseline_vs_stasya']['P@5'])} | {f(a5['baseline_vs_stasya']['P@10'])} | {f(a5['baseline_vs_stasya']['nDCG@10'])} |",
           f"| Наш подбор против разметки по скрытой правде | {f(a5['ours_vs_truth_same_pairs']['P@5'])} | {f(a5['ours_vs_truth_same_pairs']['P@10'])} | {f(a5['ours_vs_truth_same_pairs']['nDCG@10'])} |", ""]
else:
    md += ["_Независимая разметка ещё не получена (`data/pairs_labeled_stasya.json`)._", ""]
b = R["B"]
md += ["## B. Подбор", "", "| Метод | P@5 | P@10 | nDCG@10 | Есть «2» в топ-10 |", "|---|---|---|---|---|"]
for name, key in (("Наш подбор (грейд строго)", "ours"), ("Наш подбор (соседние грейды)", "ours_grade_adj"),
                  ("По ключевым словам", "keyword_baseline")):
    md.append(f"| {name} | {f(b[key]['P@5'])} | {f(b[key]['P@10'])} | {f(b[key]['nDCG@10'])} | {pc(b[key]['hit2@10'])} |")
nf = R["B_nofsp"]
md += ["", "![](img/b_matching.png)", "", "### Кандидаты без истории ФСП", "",
       f"- Доля без ФСП в топ-10: **{pc(nf['share_in_top10'])}** при доле в базе {pc(nf['share_in_pool'])}",
       f"- Сильный кандидат без ФСП (разметка 2) выше слабого с ФСП (разметка 0): **{pc(nf['strong_nofsp_above_weak_fsp'])}** из {nf['duels']} сравнений"]
if nf["example"]:
    e = nf["example"]
    md.append(f"- Пример: потребность {e[0]} — кандидат {e[1]} без ФСП на {e[2]}-м месте, кандидат {e[3]} с ФСП (не подходит) на {e[4]}-м.")
md += ["", "## C. Производительность", "",
       f"- `rank` на 300 кандидатах: **{f(R['C']['rank_ms_300'], 1)} мс**; на 3000: **{f(R['C']['rank_ms_3000'], 1)} мс** (медиана из 20 прогонов)", ""]
(OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
R["A3_templates"] = tmpl_rows
(OUT / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("\n".join(md))
