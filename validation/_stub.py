"""Stand-in for the backend core (CONTRACT 8.3) until backend/app/services is in main.

Same signatures as testing / profile / matching. Used ONLY by validation/run_all.py when the real core
cannot be imported. Numbers produced on the stub are marked as such in results.md and are not final.
"""
import hashlib
import math
import random
from datetime import datetime, timedelta

GRADES = ["junior", "middle", "senior"]
THRESHOLDS = {"junior": -0.5, "middle": 0.5, "senior": 1.5}
SPECS = ["backend", "frontend", "bas"]
RELEVANT = {"backend": {"продуктовое программирование"}, "frontend": {"продуктовое программирование"},
            "bas": {"программирование беспилотных авиационных систем", "программирование робототехники"}}


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


class _Testing:
    """Rasch model, 4 topics x 6 templates per spec, b spread from -2 to 2.5."""

    def __init__(self):
        self.TEMPLATES = {}
        for spec in SPECS:
            for t in range(4):
                for j in range(6):
                    tid = f"{spec}.t{t}.{j}"
                    b = -2.0 + 4.5 * j / 5 + (t - 1.5) * 0.1
                    self.TEMPLATES[tid] = {"id": tid, "spec": spec, "topic": f"t{t}", "b": round(b, 2),
                                           "kind": "single", "variants": 400}

    @staticmethod
    def estimate_theta(responses):
        if not responses:
            return 0.0
        theta = 0.0
        for _ in range(50):  # Newton–Raphson, clipped to [-3; 3]
            p = [1 / (1 + math.exp(-(theta - b))) for b, _ in responses]
            g = sum((1 if c else 0) - pi for (_, c), pi in zip(responses, p))
            h = -sum(pi * (1 - pi) for pi in p)
            if abs(h) < 1e-9:
                break
            step = g / h
            theta = max(-3.0, min(3.0, theta - step))
            if abs(step) < 1e-6:
                break
        return theta

    @staticmethod
    def grade_from_theta(theta):
        g = None
        for name in GRADES:
            if theta >= THRESHOLDS[name]:
                g = name
        return g

    def simulate_attempt(self, candidate_id, spec, claimed_grade, theta_true, attempt_no, rng_seed):
        rng = random.Random(rng_seed)
        pool = [t for t in self.TEMPLATES.values() if t["spec"] == spec]
        target = THRESHOLDS[claimed_grade]
        used, items, resp = set(), [], []
        for k in range(10):
            if k >= 3:
                target += 0.6 if resp[-1][1] else -0.6
            cand = [t for t in pool if t["id"] not in used]
            best = min(abs(t["b"] - target) for t in cand)
            t = rng.choice([t for t in cand if abs(t["b"] - target) <= best + 0.15])
            used.add(t["id"])
            seed = _h(candidate_id, attempt_no, t["id"])
            variant = seed % t["variants"]
            correct = rng.random() < 1 / (1 + math.exp(-(theta_true - t["b"])))
            resp.append((t["b"], correct))
            items.append({"template_id": t["id"], "b": t["b"], "correct": correct,
                          "variant_hash": f"{t['id']}#{variant}"})
        theta = self.estimate_theta(resp)
        return {"theta": theta, "grade": self.grade_from_theta(theta),
                "confirmed": theta >= THRESHOLDS[claimed_grade], "items": items}


class _Profile:
    @staticmethod
    def fsp_score(results, spec):
        if not results:
            return 0.0, [{"factor": "fsp", "text": "нет истории ФСП"}]
        pts = 0.0
        for r in results:
            base = {"winner": 3, "prize": 2, "participant": 1}[r["role"]]
            pts += base * (1.5 if r["discipline"] in RELEVANT[spec] else 1.0)
        return min(1.0, pts / 9), [{"factor": "fsp", "text": f"результатов ФСП: {len(results)}"}]


class _Matching:
    def __init__(self, profile):
        self.profile = profile

    def score(self, need, cand, now=None):
        now = now or datetime(2026, 10, 11)
        total = sum(s["weight"] for s in need["skills"])
        stack = sum(s["weight"] for s in need["skills"] if s["name"] in set(cand["skills"])) / total
        test = (max(-3, min(3, cand.get("theta") or -3)) + 3) / 6
        fsp, _ = self.profile.fsp_score(cand.get("results", []), need["spec"])
        tested = cand.get("tested_at") or now
        fresh = max(0.0, 1 - (now - tested).days / 365)
        pref = 0.5 * (cand.get("work_format") == need.get("work_format")) + \
            0.5 * (cand.get("salary_expect_from", 0) <= need.get("salary_to", 0))
        s = 100 * (0.40 * stack + 0.30 * test + 0.15 * fsp + 0.10 * fresh + 0.05 * pref)
        if cand.get("status") != "confirmed":
            s *= 0.6
        return s, [{"factor": "stack", "value": stack}, {"factor": "test", "value": test}]

    def rank(self, need, cands, grade_adj=False, fsp_only=False, extra_skills=None, limit=50):
        gi = GRADES.index(need["grade"])
        out = []
        for c in cands:
            if c["spec"] != need["spec"] or c.get("grade") is None:
                continue
            if abs(GRADES.index(c["grade"]) - gi) > (1 if grade_adj else 0):
                continue
            if fsp_only and not c.get("results"):
                continue
            s, ex = self.score(need, c)
            out.append({"candidate_id": c["id"], "score": s, "explain": ex})
        out.sort(key=lambda r: -r["score"])
        return out[:limit]

    @staticmethod
    def keyword_baseline(need, cands, limit=50):
        """Resume keyword search: skill overlap + claimed grade word, no test, no FSP."""
        out = []
        for c in cands:
            if c["spec"] != need["spec"]:
                continue
            have = set(c["skills"])
            s = sum(sk["weight"] for sk in need["skills"] if sk["name"] in have)
            s += 2 * (c["claimed_grade"] == need["grade"])
            out.append({"candidate_id": c["id"], "score": s + c["experience_years"] / 100, "explain": []})
        out.sort(key=lambda r: -r["score"])
        return out[:limit]


testing = _Testing()
profile = _Profile()
matching = _Matching(profile)
