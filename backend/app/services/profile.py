"""Модуль profile: внешние учётные записи и подтверждённые результаты, видимость профиля (CONTRACT 8.3).

Чистые функции без БД и FastAPI. Не импортирует testing и matching.
"""
import re
from datetime import date

from app.catalog import RELEVANCE_MULTIPLIER, RELEVANT_DISCIPLINES, ROLE_TITLES, SKILLS, ALL_SKILLS

ROLE_POINTS = {"winner": 1.0, "prize": 0.7, "participant": 0.2}
FSP_SATURATION = 3.0          # сумма очков, при которой fsp_score = 1
NO_FSP_TEXT = "Нет истории ФСП — оценка только по тесту"
CONTACT_FIELDS = ("email", "phone", "telegram")
# Поля, видимость которых кандидат настраивает сам (visible_fields); по умолчанию всё видно.
PRIVACY_FIELDS = ("full_name", "city", "birth_date", "about", "experience_years", "results")


def import_results(source: str, claims: dict, registry: list[dict]) -> list[dict]:
    """Записи VerifiedResult для внешней учётной записи. claims — утверждения из id_token (sub = FSP ID)."""
    sub = claims.get("sub") or claims.get("fsp_id")
    entry = next((r for r in registry if r.get("fsp_id") == sub), None)
    if entry is None:
        return []
    out = []
    for r in entry.get("results", []):
        if r.get("source", source) != source:
            continue
        out.append({"source": source, "external_id": r["external_id"], "event": r["event"],
                    "discipline": r["discipline"], "year": int(r["year"]), "place": r.get("place"),
                    "role": r["role"], "team": bool(r.get("team", False))})
    return out


def _result_text(r: dict) -> str:
    role = ROLE_TITLES.get(r["role"], r["role"])
    place = f", {r['place']} место" if r.get("place") else ""
    team = " (команда)" if r.get("team") else ""
    return f"{role} ФСП: «{r['discipline']}», {r['event']}, {r['year']}{place}{team}"


def fsp_score(results: list[dict], spec: str) -> tuple[float, list[dict]]:
    """0..1: Σ(очки роли × релевантность дисциплины) / 3, не больше 1. Нет результатов → 0 и явный текст."""
    fsp = [r for r in results or [] if r.get("source", "fsp") == "fsp"]
    if not fsp:
        return 0.0, [{"factor": "fsp", "text": NO_FSP_TEXT}]
    relevant = RELEVANT_DISCIPLINES.get(spec, set())
    pts = 0.0
    for r in fsp:
        pts += ROLE_POINTS.get(r["role"], 0.0) * (RELEVANCE_MULTIPLIER if r["discipline"] in relevant else 1.0)
    score = min(1.0, pts / FSP_SATURATION)
    best = sorted(fsp, key=lambda r: (-ROLE_POINTS.get(r["role"], 0), r["discipline"] not in relevant, -r["year"]))
    explain = [{"factor": "fsp", "text": _result_text(r) + (" — близкая дисциплина ×1,5" if r["discipline"] in relevant else "")}
               for r in best[:2]]
    if len(fsp) > 2:
        explain.append({"factor": "fsp", "text": f"Всего подтверждённых результатов ФСП: {len(fsp)}"})
    return round(score, 4), explain


def age(birth_date: date | None, today: date | None = None) -> int | None:
    if birth_date is None:
        return None
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def is_minor(birth_date: date | None, today: date | None = None) -> bool:
    a = age(birth_date, today)
    return a is not None and a < 18


def publishable(profile: dict, today: date | None = None) -> bool:
    """Профиль виден работодателям: есть согласие на обработку ПД, для несовершеннолетних — согласие родителя."""
    if not profile.get("consent_pd"):
        return False
    if is_minor(profile.get("birth_date"), today) and not profile.get("parent_consent"):
        return False
    return True


def employer_view(card: dict, contacts_visible: bool) -> dict:
    """Карточка кандидата для работодателя: контакты — только после принятия приглашения или отклика,
    остальные поля — по настройкам приватности кандидата."""
    out = dict(card)
    visible = card.get("visible_fields") or {}
    for f in PRIVACY_FIELDS:
        if visible.get(f) is False:
            out[f] = None if f != "results" else []
    if not contacts_visible:
        for f in CONTACT_FIELDS:
            out[f] = None
    out["contacts_hidden"] = not contacts_visible
    out.pop("visible_fields", None)
    return out


# ---------------------------------------------------------------- разбор резюме (текст уже извлечён из PDF)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
_TG = re.compile(r"(?<![\w.])@[A-Za-z][\w]{4,31}\b")
_EXP = re.compile(r"(?:опыт|стаж)[^\d]{0,30}(\d+(?:[.,]\d)?)\s*(?:год|лет|г\.)", re.I)
_NAME = re.compile(r"^\s*([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*$", re.M)
_GRADE = re.compile(r"\b(junior|middle|senior|джун|мидл|сеньор|синьор)\b", re.I)
_GRADE_MAP = {"джун": "junior", "мидл": "middle", "сеньор": "senior", "синьор": "senior"}

# Роли в команде и софт-скиллы: словарь «шаблон → каноническое название». Порядок — порядок в черновике.
ROLE_PATTERNS = [
    (r"тимлид|team\s*lead|техлид|tech\s*lead|руководител\w* (?:группы|команды)", "Тимлид"),
    (r"архитектор|architect", "Архитектор"),
    (r"ментор|наставни[кц]", "Ментор"),
    (r"devops|sre\b", "DevOps-инженер"),
    (r"тестировщик|\bqa\b|тестирован\w* по", "Тестировщик"),
    (r"аналитик|analyst", "Аналитик"),
    (r"оператор\w* (?:бвс|бпла|дрон)|внешн\w* пилот", "Оператор БВС"),
    (r"разработчик|программист|developer|engineer|инженер", "Разработчик"),
]
SOFT_PATTERNS = [
    (r"коммуникаб|коммуникац", "Коммуникация"),
    (r"работ\w* в команде|командн\w* работ|teamwork", "Работа в команде"),
    (r"ответственн", "Ответственность"),
    (r"лидерск|leadership", "Лидерство"),
    (r"наставничеств|менторств|mentoring", "Наставничество"),
    (r"самостоятельн", "Самостоятельность"),
    (r"аналитическ\w* мышлени|критическ\w* мышлени", "Аналитическое мышление"),
    (r"тайм-?менеджмент|управлени\w* временем|time management", "Тайм-менеджмент"),
    (r"обучаем|быстро учусь|быстро осваива", "Обучаемость"),
    (r"публичн\w* выступлени|презентаци\w* (?:решений|результатов)", "Публичные выступления"),
    (r"стрессоустойчив", "Стрессоустойчивость"),
]


def _find_all(patterns: list[tuple[str, str]], low: str) -> list[str]:
    return [name for rx, name in patterns if re.search(rx, low)]


def parse_resume_text(text: str) -> dict:
    """Черновик полей профиля из текста резюме: регулярные выражения + словари навыков, ролей и софт-скиллов
    (CONTRACT 8.1; ТЗ 2.1: ФИО, контакты, стек, грейд, роли, стаж, софт-скиллы)."""
    draft: dict = {}
    if m := _NAME.search(text):
        draft["full_name"] = m.group(1)
    if m := _EMAIL.search(text):
        draft["email"] = m.group(0)
    if m := _PHONE.search(text):
        draft["phone"] = re.sub(r"[^\d+]", "", m.group(0))
    if m := _TG.search(text.replace(draft.get("email", "\0"), "")):
        draft["telegram"] = m.group(0)
    if m := _EXP.search(text):
        draft["experience_years"] = float(m.group(1).replace(",", "."))
    low = text.lower()
    skills = [s for s in ALL_SKILLS if re.search(r"(?<![\w+#])" + re.escape(s.lower()) + r"(?![\w+#])", low)]
    draft["skills"] = skills
    draft["roles"] = _find_all(ROLE_PATTERNS, low)
    draft["soft_skills"] = _find_all(SOFT_PATTERNS, low)
    spec_hits = {spec: sum(1 for s in skills if s in vocab) for spec, vocab in SKILLS.items()}
    if skills:
        draft["spec"] = max(spec_hits, key=spec_hits.get)
    if m := _GRADE.search(text):
        g = m.group(1).lower()
        draft["claimed_grade"] = _GRADE_MAP.get(g, g)
    return draft
