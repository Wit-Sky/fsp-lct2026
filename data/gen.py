"""Synthetic data for FSP Talent (CONTRACT.md, section 8.2). Reproducible: seed = 42.

Run from repo root:  python -X utf8 data/gen.py
Writes data/{employers,candidates,needs,fsp_registry,pairs_labeled}.json
and data/stasya_cards.json (cards for independent labeling, no theta_true).
"""
import json
import math
import random
from datetime import date
from pathlib import Path

SEED = 42
OUT = Path(__file__).resolve().parent
TODAY = date(2026, 10, 11)

# --- dictionaries (CONTRACT 8.1; must match backend/app/catalog.py) ---
SKILLS = {
    "backend": ["Python", "Go", "Java", "FastAPI", "Django", "Spring", "PostgreSQL", "Redis",
                "Kafka", "Docker", "Kubernetes", "Linux", "REST", "gRPC", "SQL"],
    "frontend": ["JavaScript", "TypeScript", "React", "Vue", "Next.js", "Redux", "HTML", "CSS",
                 "Vite", "Webpack", "Jest", "REST", "Figma", "Accessibility"],
    "bas": ["Python", "C++", "Embedded C", "Linux", "MAVLink", "ArduPilot", "PX4", "ROS 2",
            "GNSS", "Kalman filter", "Computer Vision", "Docker", "SQL"],
}
# popularity weights: the same market for candidates and needs (common skills appear more often)
POPULARITY = {
    "backend": {"Python": 5, "Go": 2, "Java": 3, "FastAPI": 3, "Django": 2, "Spring": 2, "PostgreSQL": 5,
                "Redis": 3, "Kafka": 2, "Docker": 5, "Kubernetes": 2, "Linux": 4, "REST": 5, "gRPC": 1, "SQL": 5},
    "frontend": {"JavaScript": 5, "TypeScript": 5, "React": 5, "Vue": 2, "Next.js": 2, "Redux": 3, "HTML": 5,
                 "CSS": 5, "Vite": 2, "Webpack": 2, "Jest": 2, "REST": 3, "Figma": 2, "Accessibility": 1},
    "bas": {"Python": 5, "C++": 5, "Embedded C": 3, "Linux": 5, "MAVLink": 3, "ArduPilot": 3, "PX4": 3,
            "ROS 2": 3, "GNSS": 2, "Kalman filter": 2, "Computer Vision": 3, "Docker": 2, "SQL": 1},
}
DISCIPLINES = [
    "продуктовое программирование",
    "алгоритмическое программирование",
    "программирование систем информационной безопасности",
    "программирование робототехники",
    "программирование беспилотных авиационных систем",
]
GRADES = ["junior", "middle", "senior"]
THRESHOLDS = {"junior": -0.5, "middle": 0.5, "senior": 1.5}  # CONTRACT section 2


def grade_by_theta(theta):
    g = None
    for name in GRADES:
        if theta >= THRESHOLDS[name]:
            g = name
    return g


def level(g):  # None (below junior) = 0, junior = 1, ...
    return 0 if g is None else GRADES.index(g) + 1


MALE_FIRST = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
              "Никита", "Матвей", "Роман", "Егор", "Арсений", "Иван", "Денис", "Евгений", "Тимофей", "Владислав",
              "Павел", "Глеб", "Константин", "Ярослав", "Фёдор"]
FEMALE_FIRST = ["Анастасия", "Мария", "Анна", "Виктория", "Екатерина", "Наталья", "Марина", "Полина", "Дарья",
                "Алиса", "Ксения", "Елизавета", "Софья", "Валерия", "Ольга", "Татьяна", "Юлия", "Вероника",
                "Алёна", "Ирина"]
MALE_PATR = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Алексеевич", "Игоревич", "Михайлович",
             "Владимирович", "Николаевич", "Олегович", "Павлович", "Евгеньевич", "Викторович", "Юрьевич"]
SURNAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков",
            "Фёдоров", "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов", "Егоров", "Павлов", "Козлов",
            "Степанов", "Николаев", "Орлов", "Андреев", "Макаров", "Никитин", "Захаров", "Зайцев", "Соловьёв",
            "Борисов", "Яковлев", "Григорьев", "Романов", "Воробьёв", "Сергеев", "Кузьмин", "Фролов",
            "Александров", "Дмитриев", "Королёв", "Гусев", "Киселёв", "Ильин", "Максимов", "Поляков",
            "Сорокин", "Виноградов", "Ковалёв", "Белов", "Медведев", "Антонов", "Тарасов"]
TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r",
                     "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
CITIES = [("Москва", 45), ("Санкт-Петербург", 15), ("Казань", 7), ("Новосибирск", 7), ("Екатеринбург", 7),
          ("Нижний Новгород", 6), ("Самара", 5), ("Томск", 4), ("Иннополис", 4)]
FSP_EVENTS = ["Чемпионат России по спортивному программированию", "Кубок России по спортивному программированию",
              "Всероссийский хакатон ФСП", "Первенство России по спортивному программированию",
              "Региональные соревнования по спортивному программированию"]

EMPLOYERS = [
    # name, field, description, spec plan for its 3 needs
    ("ООО «Облачные решения Север»", "облачные сервисы", "Разрабатываем платформу хранения и обработки данных для логистики.",
     ["backend", "backend", "frontend"]),
    ("АО «ФинПоток»", "финтех", "Платёжные сервисы и мобильный банкинг для малого бизнеса.", ["backend", "frontend", "backend"]),
    ("ООО «Медиатека Плюс»", "медиа", "Стриминговый сервис образовательного видео.", ["frontend", "frontend", "backend"]),
    ("ООО «ГородДанных»", "умный город", "Цифровые сервисы для транспорта и ЖКХ.", ["backend", "frontend", "backend"]),
    ("ООО «Ритейл Технологии»", "электронная коммерция", "Маркетплейс товаров для дома и сада.", ["frontend", "backend", "frontend"]),
    ("ООО «ЭдТех Лаб»", "образование", "Онлайн-тренажёры по программированию для школьников.", ["frontend", "backend", "frontend"]),
    ("АО «Индустриальные системы»", "промышленность", "Системы мониторинга производственного оборудования.", ["backend", "backend", "frontend"]),
    ("ООО «МедСервис Онлайн»", "здравоохранение", "Сервис записи к врачу и телемедицины.", ["backend", "frontend", "frontend"]),
    ("ООО «АэроСкан Сервис»", "эксплуатант БВС", "Аэрофотосъёмка и мониторинг линейных объектов беспилотниками.", ["bas", "bas", "backend"]),
    ("ООО «Небесный Патруль»", "эксплуатант БВС", "Доставка и патрулирование с помощью беспилотных авиационных систем.", ["bas", "bas", "frontend"]),
]
TITLES = {"backend": "Backend-разработчик", "frontend": "Frontend-разработчик", "bas": "Разработчик ПО БАС"}
SALARY = {  # rubles per month, gross reference ranges by grade
    "junior": (80_000, 150_000), "middle": (170_000, 300_000), "senior": (300_000, 480_000)}


def translit(s):
    return "".join(TRANSLIT.get(ch, ch) for ch in s.lower())


def weighted_sample(rng, items, weights, k):
    pool, w, out = list(items), list(weights), []
    for _ in range(min(k, len(pool))):
        i = rng.choices(range(len(pool)), weights=w)[0]
        out.append(pool.pop(i))
        w.pop(i)
    return out


def rand_birth(rng, age_from, age_to):
    age = rng.randint(age_from, age_to)
    y = TODAY.year - age - (1 if rng.random() < 0.5 else 0)
    d = date(y, rng.randint(1, 12), rng.randint(1, 28))
    # keep exact age inside the band
    a = TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))
    if a < age_from:
        d = d.replace(year=d.year - 1)
    elif a > age_to:
        d = d.replace(year=d.year + 1)
    return d


def age_of(d):
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))


def gen_employers(rng):
    out = []
    for i, (name, field, desc, _) in enumerate(EMPLOYERS, start=1):
        slug = f"company{i:02d}"
        out.append({
            "id": i, "name": name, "inn": "77" + "".join(str(rng.randint(0, 9)) for _ in range(8)),
            "field": field, "description": desc,
            "contacts": f"hr@{slug}.example.ru, +7 900 {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}",
            "owner_email": f"hr@{slug}.example.ru",
        })
    return out


def gen_results(rng, spec, age):
    n = rng.randint(1, 5)
    res = []
    for _ in range(n):
        if spec == "bas" and rng.random() < 0.6:
            disc = rng.choice(DISCIPLINES[3:])  # БАС or robotics
        else:
            disc = rng.choice(DISCIPLINES)
        r = rng.random()
        role = "winner" if r < 0.10 else ("prize" if r < 0.35 else "participant")
        place = 1 if role == "winner" else (rng.choice([2, 3]) if role == "prize" else None)
        res.append({
            "source": "fsp", "external_id": f"FSP-RES-{rng.randint(10000, 99999)}",
            "event": rng.choice(FSP_EVENTS), "discipline": disc,
            "year": rng.randint(max(2023, TODAY.year - (age - 14)), 2026),
            "place": place, "role": role, "team": rng.random() < 0.7,
        })
    res.sort(key=lambda x: x["year"])
    return res


def gen_candidates(rng):
    n = 300
    specs = ["backend"] * 135 + ["frontend"] * 135 + ["bas"] * 30
    rng.shuffle(specs)
    minors = set(rng.sample(range(n), 15))            # 5 % aged 16–17
    claim_kind = ["honest"] * 210 + ["over"] * 60 + ["under"] * 30
    rng.shuffle(claim_kind)
    has_fsp = set(rng.sample(range(n), 120))          # 40 %
    cities, cw = zip(*CITIES)
    used_emails = set()
    out = []
    for i in range(n):
        cid = i + 1
        spec = specs[i]
        theta = max(-2.5, min(2.5, rng.gauss(0, 1)))
        male = rng.random() < 0.75
        first = rng.choice(MALE_FIRST if male else FEMALE_FIRST)
        sur = rng.choice(SURNAMES) + ("" if male else "а")
        patr = rng.choice(MALE_PATR)
        if not male:
            patr = patr[:-2] + "на"
        full_name = f"{sur} {first} {patr}"
        birth = rand_birth(rng, 16, 17) if i in minors else rand_birth(rng, 18, 40)
        age = age_of(birth)
        # experience and skill count correlate with theta, with noise
        exp = 2.5 + 2.2 * theta + rng.gauss(0, 2.0)
        exp = round(max(0.0, min(exp, age - 16, 20.0)), 1)
        k = int(round(6 + 1.2 * theta + rng.gauss(0, 1.3)))
        k = max(4, min(9, k))
        pop = POPULARITY[spec]
        skills = weighted_sample(rng, SKILLS[spec], [pop[s] for s in SKILLS[spec]], k)
        # claimed grade
        honest = grade_by_theta(theta) or "junior"
        gi = GRADES.index(honest)
        kind = claim_kind[i]
        if kind == "over":
            gi = min(2, gi + 1)
        elif kind == "under":
            gi = max(0, gi - 1)
        claimed = GRADES[gi]
        base = f"{translit(first)}.{translit(sur)}"
        email = f"{base}@example.ru"
        j = 2
        while email in used_emails:
            email = f"{base}{j}@example.ru"
            j += 1
        used_emails.add(email)
        lo = SALARY[claimed][0]
        salary = int(round(lo * rng.uniform(0.9, 1.4), -4))
        results = gen_results(rng, spec, age) if i in has_fsp else []
        out.append({
            "id": cid, "email": email, "full_name": full_name, "birth_date": birth.isoformat(),
            "phone": f"+7 900 {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}",
            "telegram": f"@{translit(first)}_{translit(sur)}{rng.randint(1, 99)}",
            "city": rng.choices(cities, weights=cw)[0],
            "work_format": rng.choice(["office", "remote", "hybrid"]),
            "salary_expect_from": salary, "experience_years": exp, "spec": spec, "claimed_grade": claimed,
            "skills": skills,
            "about": f"{TITLES[spec]}, опыт {exp:g} г. Основной стек: {', '.join(skills[:3])}.",
            "fsp_id": f"FSP-{100000 + cid}" if results else None,
            "results": results, "theta_true": round(theta, 3),
        })
    return out


def gen_needs(rng):
    out, nid = [], 1
    for eid, (_, _, _, plan) in enumerate(EMPLOYERS, start=1):
        for spec in plan:
            grade = rng.choices(GRADES, weights=[3, 4, 2])[0]
            pop = POPULARITY[spec]
            k = rng.randint(3, 6)
            names = weighted_sample(rng, SKILLS[spec], [pop[s] for s in SKILLS[spec]], k)
            skills = [{"name": s, "weight": rng.randint(1, 3)} for s in names]
            lo, hi = SALARY[grade]
            s_from = int(round(rng.uniform(lo, (lo + hi) / 2), -4))
            s_to = int(round(rng.uniform(max(s_from + 30_000, (lo + hi) / 2), hi * 1.1), -4))
            stype = rng.choice(["gross", "net"])
            if stype == "net":
                s_from, s_to = int(round(s_from * 0.87, -4)), int(round(s_to * 0.87, -4))
            out.append({
                "id": nid, "employer_id": eid, "title": f"{TITLES[spec]} ({grade})", "spec": spec, "grade": grade,
                "skills": skills,
                "description": f"Ищем {TITLES[spec].lower()} уровня {grade}. Ключевое: {', '.join(names)}.",
                "salary_from": s_from, "salary_to": s_to, "salary_type": stype,
                "work_format": rng.choice(["office", "remote", "hybrid"]), "published": rng.random() < 0.5,
            })
            nid += 1
    return out


def coverage(need, cand):
    total = sum(s["weight"] for s in need["skills"])
    have = set(cand["skills"])
    return sum(s["weight"] for s in need["skills"] if s["name"] in have) / total


def label(need, cand):
    """Ground truth by HIDDEN theta_true, independent of the matching formula (validation/README.md)."""
    if cand["spec"] != need["spec"]:
        return 0
    gap = abs(level(grade_by_theta(cand["theta_true"])) - level(need["grade"]))
    cov = coverage(need, cand)
    if gap == 0 and cov >= 0.7:
        return 2
    if (gap == 0 and cov >= 0.4) or (gap == 1 and cov >= 0.4):
        return 1
    return 0


def main():
    rng = random.Random(SEED)
    employers = gen_employers(rng)
    candidates = gen_candidates(rng)
    needs = gen_needs(rng)

    registry = [{"fsp_id": c["fsp_id"], "full_name": c["full_name"], "email": c["email"], "results": c["results"]}
                for c in candidates if c["fsp_id"]]
    # 5 free registry entries for the demo of FSP ID linking (no candidate profile yet)
    for k in range(5):
        spec = ["backend", "frontend", "bas", "backend", "frontend"][k]
        first, sur = rng.choice(MALE_FIRST), rng.choice(SURNAMES)
        registry.append({"fsp_id": f"FSP-9{k:05d}", "full_name": f"{sur} {first} {rng.choice(MALE_PATR)}",
                         "email": f"demo{k + 1}@example.ru", "results": gen_results(rng, spec, 20)})

    pairs = {}
    for nd in needs:
        lab = {str(c["id"]): label(nd, c) for c in candidates}
        pairs[str(nd["id"])] = {cid: v for cid, v in lab.items() if v > 0}

    # cards for independent labeling: 10 needs x 20 candidates of the same spec, no theta_true and no score.
    # Mix by hidden label (≈5/7/8) so that the set is not all zeros; order shuffled.
    srng = random.Random(SEED + 1)
    cards_needs = []
    pick = [n for n in needs if n["spec"] == "backend"][:4] + [n for n in needs if n["spec"] == "frontend"][:4] \
        + [n for n in needs if n["spec"] == "bas"][:2]
    for nd in pick:
        same = [c for c in candidates if c["spec"] == nd["spec"]]
        by = {v: [c for c in same if label(nd, c) == v] for v in (0, 1, 2)}
        chosen = []
        for v, want in ((2, 5), (1, 7)):
            chosen += srng.sample(by[v], min(want, len(by[v])))
        rest = [c for c in same if c not in chosen]
        chosen += srng.sample(rest, 20 - len(chosen))
        srng.shuffle(chosen)
        cards_needs.append({
            "need": {k: nd[k] for k in ("id", "title", "spec", "grade", "skills", "description",
                                        "salary_from", "salary_to", "salary_type", "work_format")},
            "candidates": [{
                "candidate_id": c["id"], "spec": c["spec"], "claimed_grade": c["claimed_grade"],
                "skills": c["skills"], "experience_years": c["experience_years"],
                "fsp_results": [{"discipline": r["discipline"], "year": r["year"], "role": r["role"]} for r in c["results"]],
            } for c in chosen],
        })

    files = {"employers.json": employers, "candidates.json": candidates, "needs.json": needs,
             "fsp_registry.json": registry, "pairs_labeled.json": pairs, "stasya_cards.json": cards_needs}
    for name, obj in files.items():
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    # summary for validation/README.md
    from collections import Counter
    print("spec:", Counter(c["spec"] for c in candidates))
    print("minors:", sum(age_of(date.fromisoformat(c["birth_date"])) < 18 for c in candidates))
    print("fsp:", sum(1 for c in candidates if c["fsp_id"]))
    print("grade_by_theta:", Counter(grade_by_theta(c["theta_true"]) for c in candidates))
    print("claimed:", Counter(c["claimed_grade"] for c in candidates))
    print("needs spec/grade:", Counter((n["spec"], n["grade"]) for n in needs))
    l2 = [sum(1 for v in p.values() if v == 2) for p in pairs.values()]
    l1 = [sum(1 for v in p.values() if v == 1) for p in pairs.values()]
    print("label2 per need:", l2)
    print("label1 per need:", l1)
    r = [(c["theta_true"], c["experience_years"]) for c in candidates]
    mx = sum(a for a, _ in r) / len(r); my = sum(b for _, b in r) / len(r)
    cov = sum((a - mx) * (b - my) for a, b in r)
    print("corr(theta, exp) =", round(cov / math.sqrt(sum((a - mx) ** 2 for a, _ in r) * sum((b - my) ** 2 for _, b in r)), 3))


if __name__ == "__main__":
    main()
