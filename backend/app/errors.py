"""Единый формат ошибок: {detail: str, code: str} (CONTRACT 6)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorOut(BaseModel):
    detail: str
    code: str


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str, **extra):
        self.status, self.code, self.detail, self.extra = status, code, detail, extra


def not_found(what: str = "Объект") -> ApiError:
    return ApiError(404, "not_found", f"{what} не найден")


def forbidden(detail: str = "Нет доступа") -> ApiError:
    return ApiError(403, "forbidden", detail)


def responses(*codes: int) -> dict:
    """Описание кодов ошибок для OpenAPI."""
    text = {400: "Неверный запрос", 401: "Нет или неверный токен", 403: "Нет доступа / кулдаун",
            404: "Не найдено", 409: "Конфликт", 422: "Ошибка валидации"}
    return {c: {"model": ErrorOut, "description": text.get(c, "Ошибка")} for c in codes}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse({"detail": e.detail, "code": e.code, **e.extra}, status_code=e.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(e.status_code, "error")
        return JSONResponse({"detail": str(e.detail), "code": code}, status_code=e.status_code, headers=e.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        errs = e.errors()
        first = errs[0] if errs else {}
        loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        detail = f"{loc}: {first.get('msg', 'invalid')}" if loc else first.get("msg", "invalid")
        return JSONResponse({"detail": detail, "code": "validation_error",
                             "errors": [{"loc": list(x.get("loc", [])), "msg": x.get("msg")} for x in errs]},
                            status_code=422)
