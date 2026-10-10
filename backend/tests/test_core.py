"""Чистые модули ядра: уникальность вариантов, θ по Раша, симуляция, границы модулей."""
import ast
import random
from pathlib import Path

from app.catalog import THRESHOLDS
from app.services import matching, profile, testing

SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"


def test_variants_differ_between_candidates_and_reproduce():
    for tid, t in testing.TEMPLATES.items():
        a1 = t.generate(testing.variant_seed(1, 1, tid))
        a2 = t.generate(testing.variant_seed(1, 1, tid))
        assert a1 == a2, f"{tid}: вариант не воспроизводится"
    differ = 0
    for tid, t in testing.TEMPLATES.items():
        hashes = {testing.variant_hash(t.generate(testing.variant_seed(c, 1, tid))) for c in range(1, 21)}
        differ += len(hashes) > 1
        assert len(hashes) > 1, f"{tid}: у 20 кандидатов одинаковый вариант"
    assert differ == len(testing.TEMPLATES)


def test_generated_answers_are_consistent():
    for tid, t in testing.TEMPLATES.items():
        for s in range(30):
            item = t.generate(s)
            assert testing.check_answer(item, item["answer"]), tid
            if item["kind"] == "single":
                assert item["answer"] in item["options"] and len(set(item["options"])) == len(item["options"]), tid


def test_bank_size():
    for spec in ("backend", "frontend", "bas"):
        topics = testing.topics_for(spec)
        assert len(topics) >= 3
        for topic in topics:
            assert sum(1 for t in testing.TEMPLATES.values() if t.spec == spec and t.topic == topic) >= 6


def test_estimate_theta_monotone():
    rng = random.Random(0)
    bs = [rng.uniform(-2, 2) for _ in range(10)]
    prev = -10.0
    for k in range(11):
        theta = testing.estimate_theta([(b, i < k) for i, b in enumerate(bs)])
        assert theta >= prev
        assert -3 <= theta <= 3
        prev = theta
    assert testing.estimate_theta([(0.0, True)] * 10) > testing.estimate_theta([(0.0, True)] * 5 + [(0.0, False)] * 5)


def test_simulation_separates_strong_and_weak():
    def senior_rate(theta_true):
        return sum(testing.simulate_attempt(i, "backend", "senior", theta_true, 1, i)["confirmed"] for i in range(150)) / 150
    assert senior_rate(2.0) > senior_rate(-1.0) + 0.4


def test_attempt_flow_and_adaptivity():
    state = testing.build_attempt(7, "frontend", "middle", 1)
    seen = set()
    while (item := testing.next_item(state)) is not None:
        assert item["template_id"] not in seen
        seen.add(item["template_id"])
        pub = testing.public_item(item, state)
        assert "answer" not in pub and "b" not in pub
        testing.submit(state, item["item_id"], item["answer"])
    res = testing.finish(state)
    assert res["total"] == 10 and res["correct"] == 10
    assert res["confirmed"] and res["theta"] >= THRESHOLDS["middle"]
    bs = [r["b"] for r in state["responses"]]
    assert bs[-1] > bs[0], "после верных ответов сложность должна расти"


def test_fsp_score_without_history():
    score, explain = profile.fsp_score([], "backend")
    assert score == 0 and "Нет истории ФСП" in explain[0]["text"]


def test_matching_candidate_without_fsp():
    need = {"spec": "backend", "grade": "middle", "skills": [{"name": "Python", "weight": 2}], "salary_to": 300000,
            "work_format": "remote"}
    cand = {"id": 1, "spec": "backend", "grade": "middle", "status": "confirmed", "theta": 0.9, "skills": ["Python"],
            "results": [], "tested_at": None, "work_format": "remote", "salary_expect_from": 200000}
    ranked = matching.rank(need, [cand], fsp_fn=profile.fsp_score)
    assert ranked and any("Нет истории ФСП" in e["text"] for e in ranked[0]["explain"])
    unconf = matching.rank(need, [{**cand, "status": "unconfirmed"}], fsp_fn=profile.fsp_score)
    assert unconf[0]["score"] < ranked[0]["score"]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names.add(mod)
            names |= {f"{mod}.{a.name}" for a in node.names}
    return names


def test_module_boundaries():
    """testing / profile / matching не импортируют друг друга, SQLAlchemy и FastAPI (ADR 0001)."""
    mods = ("testing", "profile", "matching")
    for m in mods:
        imps = _imports(SERVICES / f"{m}.py")
        for other in mods:
            if other != m:
                assert not any(i.endswith(f"services.{other}") or i == f"app.services.{other}" for i in imps), (m, other)
        assert not any(i.split(".")[0] in ("sqlalchemy", "fastapi", "starlette") for i in imps), m
        assert not any(i.startswith("app.models") or i.startswith("app.db") for i in imps), m
