import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, errors
from app.routers import auth, employer, me, tests, vacancies

logging.basicConfig(level=logging.INFO)

DESCRIPTION = """
API платформы подбора ИТ-специалистов (спецтрек ФСП, ЛЦТ-2026).

**Обратная механика:** кандидат проходит адаптивный тест на заявленный грейд и попадает в категорию
(специализация + грейд); работодатель описывает потребность, получает ранжированную подборку с объяснением
и сам направляет адресное приглашение с зарплатой. Контакты кандидата открываются только после принятия
приглашения или собственного отклика.

Авторизация — `Authorization: Bearer <JWT>` (24 часа). Ошибки — `{detail, code}`.
Для жюри: `POST /api/auth/demo/candidate` и `POST /api/auth/demo/employer`.
"""

app = FastAPI(title="FSP Talent API", version="1.0.0", description=DESCRIPTION,
              docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
errors.install(app)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["system"], summary="Проверка живости")
async def health():
    return {"status": "ok"}


for r in (auth.router, me.router, tests.router, employer.router, vacancies.router, vacancies.catalog_router):
    api.include_router(r)
app.include_router(api)
