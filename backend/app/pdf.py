"""Стандартизированный PDF-профиль кандидата (reportlab, кириллический шрифт DejaVuSans из app/fonts)."""
import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.catalog import GRADE_TITLES, ROLE_TITLES, SPECS, WORK_FORMAT_TITLES

FONT_DIR = Path(__file__).parent / "fonts"
_font = "Helvetica"
if (FONT_DIR / "DejaVuSans.ttf").exists():
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_DIR / "DejaVuSans.ttf")))
    _font = "DejaVuSans"

PURPLE = colors.HexColor("#520978")
PINK = colors.HexColor("#FF0053")
STATUS = {"confirmed": "подтверждён тестом", "unconfirmed": "не подтверждён", "none": "тест не пройден"}


def _esc(s) -> str:
    return str(s if s is not None else "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_profile(c: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Профиль кандидата")
    h1 = ParagraphStyle("h1", fontName=_font, fontSize=20, leading=24, textColor=PURPLE)
    h2 = ParagraphStyle("h2", fontName=_font, fontSize=13, leading=17, textColor=PINK, spaceBefore=8, spaceAfter=4)
    p = ParagraphStyle("p", fontName=_font, fontSize=10, leading=14)
    story = [Paragraph(_esc(c.get("full_name") or "Кандидат"), h1),
             Paragraph("Стандартизированный профиль · платформа подбора ИТ-специалистов ФСП", p), Spacer(1, 6)]

    grade = c.get("grade")
    rows = [["Специализация", SPECS.get(c.get("spec"), c.get("spec") or "—")],
            ["Грейд", f"{GRADE_TITLES.get(grade, '—') if grade else '—'} ({STATUS.get(c.get('status') or 'none')})"],
            ["θ (шкала Раша)", f"{c['theta']:.2f}" if c.get("theta") is not None else "—"],
            ["Опыт", f"{c['experience_years']:g} г." if c.get("experience_years") is not None else "—"],
            ["Город", c.get("city") or "—"],
            ["Формат работы", WORK_FORMAT_TITLES.get(c.get("work_format"), "—")],
            ["Ожидания по зарплате", f"от {c['salary_expect_from']:,} ₽".replace(",", " ") if c.get("salary_expect_from") else "—"],
            ["Email", c.get("email") or "—"], ["Телефон", c.get("phone") or "—"], ["Telegram", c.get("telegram") or "—"]]
    t = Table([[Paragraph(_esc(a), p), Paragraph(_esc(b), p)] for a, b in rows], colWidths=[50 * mm, 120 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#8A83D1")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFD6E4")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Paragraph("Стек", h2), Paragraph(_esc(", ".join(c.get("skills") or []) or "—"), p)]
    if c.get("about"):
        story += [Paragraph("О себе", h2), Paragraph(_esc(c["about"]), p)]
    story.append(Paragraph("Подтверждённые результаты ФСП", h2))
    res = c.get("results") or []
    if not res:
        story.append(Paragraph("Нет истории ФСП — оценка только по тесту.", p))
    for r in res:
        place = f", {r['place']} место" if r.get("place") else ""
        story.append(Paragraph(_esc(f"{ROLE_TITLES.get(r['role'], r['role'])}: {r['discipline']} — {r['event']}, {r['year']}{place}"
                                    + (" (команда)" if r.get("team") else "")), p))
    doc.build(story)
    return buf.getvalue()
