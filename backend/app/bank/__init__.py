"""Банк параметрических шаблонов заданий. Импорт модулей регистрирует шаблоны в REGISTRY."""
from app.bank._base import REGISTRY, Template  # noqa: F401
from app.bank import (backend_python, backend_http, backend_sql, backend_arch,  # noqa: F401
                      frontend_js, frontend_react, frontend_css, frontend_web,
                      bas_mavlink, bas_nav, bas_autopilot)
