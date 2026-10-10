"""Build docs/FSP_Talent_Документация.pdf from docs/src/*.md + generated sections.

Run from repo root:  python -X utf8 docs/build_pdf.py
Generated sections: 4 (validation/results.md), 6 (backend OpenAPI), 7 (requirements.txt, package.json,
docker-compose.yml), 8 (docs/deploy.md if present). Missing inputs are reported in the PDF and on stdout.
Needs: pip install markdown; Chrome or Edge for --print-to-pdf.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SRC = DOCS / "src"
OUT_PDF = DOCS / "FSP_Talent_Документация.pdf"
TMP_HTML = DOCS / "_build.html"
MISSING = []

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 18mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1C1D22; }
h1 { color: #520978; font-size: 17pt; border-bottom: 2px solid #FF0053; padding-bottom: 3px; page-break-before: always; }
h1.first { page-break-before: avoid; }
h2 { color: #310F53; font-size: 13pt; margin-top: 16px; }
h3 { color: #520978; font-size: 11.5pt; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5pt; page-break-inside: auto; }
th, td { border: 1px solid #c9c3e6; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #FFD6E4; }
tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f3f0fa; padding: 0 2px; }
pre { background: #f3f0fa; padding: 6px; font-size: 8.5pt; white-space: pre-wrap; }
img { max-width: 60%; display: block; margin: 6px auto; }
.title { text-align: center; margin-top: 70mm; }
.title h1 { border: none; font-size: 26pt; page-break-before: avoid; }
.title p { font-size: 13pt; color: #310F53; }
.warn { background: #FFD6E4; border-left: 4px solid #FF0053; padding: 6px 10px; }
"""


def read(p: Path):
    return p.read_text(encoding="utf-8") if p.exists() else None


def warn(text):
    MISSING.append(text)
    return f'<div class="warn">{text}</div>\n'


def section_validation():
    res = read(ROOT / "validation" / "results.md")
    rule = read(ROOT / "validation" / "README.md")
    md = "# 4. Процедура валидации и результаты\n\n"
    md += ("## Процедура\n"
           "1. Синтетическая база (`data/gen.py`, seed = 42): у каждого кандидата есть скрытая способность θ_true, "
           "которую не видят ни тест, ни подбор.\n"
           "2. **Тестирование:** каждый кандидат проходит симуляцию теста дважды (ответ верен с вероятностью по модели Раша "
           "от θ_true); считаются повторяемость, точность против скрытой правды, разделяющая сила шаблонов, устойчивость к утечке.\n"
           "3. **Подбор:** эталон пар «потребность — кандидат» размечен по скрытой правде, а не по формуле подбора "
           "(правило ниже), поэтому проверка не замкнута сама на себя. Сравнение с поиском по ключевым словам.\n"
           "4. **Вторая независимая разметка** 200 пар (10 потребностей × 20 карточек) сделана вслепую: разметчик видел только "
           "карточки (специализация, заявленный грейд, навыки, стаж, результаты ФСП) без θ_true, без скора системы и без первой "
           "разметки. Разметку выполнила языковая модель в отдельном контексте; сомнительные случаи — `validation/stasya_doubts.md`. "
           "Согласие разметчиков — каппа Коэна.\n\n")
    if rule:
        rule_ru = rule.split("## Ground-truth labels", 1)[-1].split("## Independent", 1)[0]
        md += "## Правило эталонной разметки\n" + rule_ru.replace("(`data/pairs_labeled.json`)", "") + "\n"
    if res:
        body = res.split("\n", 1)[1]
        body = body.replace("](img/", "](../validation/img/")
        body = re.sub(r"^## ", "## ", body, flags=re.M)
        if "STUB" in body:
            md += warn("Цифры получены на заглушке ядра (validation/_stub.py), не на коде бэкенда. Перед сдачей — перепрогнать.")
        md += body
    else:
        md += warn("Нет validation/results.md — запустить validation/run_all.py.")
    return md


def section_api():
    md = "# 6. Описание API\n\nПрефикс `/api`, авторизация — JWT в заголовке `Authorization: Bearer`. " \
         "Полная спецификация — Swagger стенда `/docs` и файл `docs/openapi.json`.\n\n"
    spec_p = DOCS / "openapi.json"
    if not spec_p.exists():
        try:
            sys.path.insert(0, str(ROOT / "backend"))
            from app.main import app  # noqa: E402
            spec_p.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            md += warn(f"OpenAPI бэкенда недоступен ({type(e).__name__}); ниже — таблица из CONTRACT.md, раздел 6.")
            contract = read(ROOT / "CONTRACT.md") or ""
            m = re.search(r"## 6\. API.*?\n(\|.*?)\n\n", contract, flags=re.S)
            return md + (m.group(1) if m else "") + "\n"
    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    md += "| Метод | Путь | Назначение |\n|---|---|---|\n"
    for path, ops in spec.get("paths", {}).items():
        for meth, op in ops.items():
            if meth.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            summ = (op.get("summary") or op.get("description") or "").split("\n")[0]
            md += f"| {meth.upper()} | `{path}` | {summ} |\n"
    return md


def section_libs():
    md = "# 7. Библиотеки и компоненты с версиями\n\n"
    req = read(ROOT / "backend" / "requirements.txt")
    if req:
        md += "## Бэкенд (`backend/requirements.txt`)\n\n| Пакет | Версия |\n|---|---|\n"
        for line in req.splitlines():
            line = line.split("#")[0].strip()
            if line:
                m = re.match(r"([A-Za-z0-9_.\-\[\]]+)\s*(.*)", line)
                md += f"| {m.group(1)} | {m.group(2) or '—'} |\n"
    else:
        md += warn("Нет backend/requirements.txt.")
    pkg = read(ROOT / "frontend" / "package.json")
    if pkg:
        j = json.loads(pkg)
        md += "\n## Фронтенд (`frontend/package.json`)\n\n| Пакет | Версия |\n|---|---|\n"
        for sec in ("dependencies", "devDependencies"):
            for k, v in j.get(sec, {}).items():
                md += f"| {k} | {v} |\n"
    else:
        md += warn("Нет frontend/package.json.")
    dc = read(ROOT / "docker-compose.yml")
    if dc:
        imgs = re.findall(r"image:\s*([^\s]+)", dc)
        md += "\n## Docker-образы (`docker-compose.yml`)\n\n" + "".join(f"- `{i}`\n" for i in imgs)
    else:
        md += warn("Нет docker-compose.yml.")
    md += "\n## Валидация и документация\n\n- Python 3.12+, matplotlib, numpy (графики валидации); markdown (сборка документации).\n"
    return md


def section_deploy():
    dep = read(DOCS / "deploy.md")
    if dep:
        return dep
    md = "# 8. Сборка, развёртывание и локальный запуск\n\n"
    md += ("```\ngit clone https://github.com/Wit-Sky/fsp-lct2026\ncd fsp-lct2026\ncp .env.example .env\n"
           "docker compose up --build\n```\n\nПосле старта: веб-приложение — http://localhost/, Swagger — http://localhost/api/docs.\n"
           "Демо-доступы: кнопки «Войти как кандидат» и «Войти как работодатель» на главной "
           "(`candidate@demo.fsp`, `employer@demo.fsp`).\n\n")
    md += warn("Раздел будет уточнён по README и docker-compose.yml капитана (docs/deploy.md).")
    return md


def main():
    parts = ['<div class="title"><h1>FSP Talent</h1><p>Платформа подбора ИТ-специалистов с подтверждённым грейдом</p>'
             '<p>ЛЦТ-2026, спецтрек ФСП · МГТУ ГА</p><p>Сопроводительная документация</p></div>']
    chunks = {
        0: read(SRC / "00_approach.md"), 1: read(SRC / "01_architecture.md"), 2: read(SRC / "02_testing.md"),
        3: read(SRC / "03_matching.md"), 4: section_validation(), 5: read(SRC / "05_fsp.md"),
        6: section_api(), 7: section_libs(), 8: section_deploy(), 9: read(SRC / "09_concepts.md"),
    }
    for k in sorted(chunks):
        if chunks[k] is None:
            chunks[k] = f"# {k}.\n\n" + warn(f"Нет исходника раздела {k}.")
        parts.append(markdown.markdown(chunks[k], extensions=["tables", "fenced_code"]))
    html = ("<!doctype html><html lang='ru'><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
            + "\n".join(parts) + "</body></html>")
    TMP_HTML.write_text(html, encoding="utf-8")
    browser = next((p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                                shutil.which("chromium"), shutil.which("google-chrome")] if p and Path(p).exists()), None)
    if not browser:
        sys.exit("Chrome/Edge not found")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT_PDF}", TMP_HTML.as_uri()], check=True, capture_output=True)
    TMP_HTML.unlink()
    print("PDF:", OUT_PDF)
    if MISSING:
        print("Не хватает:", *MISSING, sep="\n - ")


if __name__ == "__main__":
    main()
