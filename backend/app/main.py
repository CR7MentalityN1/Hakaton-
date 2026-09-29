from contextlib import asynccontextmanager
from pathlib import Path
import logging
import uuid
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.cache import cache
from app.db.session import engine
from app.schemas.dto import ErrorOut
from app.api.router import router


@asynccontextmanager
async def lifespan(app):
    # Alembic runs before Uvicorn in the container entrypoint. No create_all here.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="Ростелеком ИТ Школа — CRM",
    version="2.0.0",
    description="Production-like учебный сервис. OIDC Keycloak, RBAC и серверная область доступа. Все ошибки имеют code/message/details.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "X-Request-ID", "Server-Timing"],
)


@app.middleware("http")
async def headers(request: Request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        length = 0
    if length > settings.upload_limit + 65536:
        return JSONResponse(
            {
                "code": "UPLOAD_TOO_LARGE",
                "message": f"Максимум {settings.max_upload_mb} МБ",
                "details": {},
            },
            status_code=413,
        )
    response = await call_next(request)
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Cache-Control": "no-store",
            "Server-Timing": f"app;dur={(time.perf_counter() - start) * 1000:.2f}",
        }
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    data = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}}
    )
    return JSONResponse(jsonable_encoder(data), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(
        {
            "code": "VALIDATION_ERROR",
            "message": "Проверьте поля запроса",
            "details": {
                "fields": [
                    {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                    for e in exc.errors()
                ]
            },
        },
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {
            "code": "DATA_CONFLICT",
            "message": "Запись уже существует или используется связанными данными",
            "details": {},
        },
        status_code=409,
    )


@app.exception_handler(Exception)
async def internal_error(request, exc):
    logging.getLogger("crm").exception("Request failed")
    return JSONResponse(
        {
            "code": "INTERNAL_ERROR",
            "message": "Не удалось выполнить операцию. Обратитесь к администратору.",
            "details": {},
        },
        status_code=500,
    )


@app.get(
    "/health",
    tags=["Система"],
    summary="Готовность API и соединение с PostgreSQL/Redis",
    response_model=dict[str, str],
    responses={503: {"model": ErrorOut}},
)
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            503,
            {
                "code": "DATABASE_UNAVAILABLE",
                "message": "База недоступна",
                "details": {},
            },
        )
    try:
        cache.client.ping()
        redis_state = "ok"
    except Exception:
        redis_state = "degraded"
    return {"status": "ok", "database": "ok", "redis": redis_state, "auth": "keycloak"}


for route in router.routes:
    if hasattr(route, "description") and not route.description:
        route.description = route.summary or "Операция CRM с проверкой прав доступа."
app.include_router(router)
docs = Path(__file__).resolve().parents[2] / "docs"
if not docs.exists():
    docs = Path(__file__).resolve().parents[3] / "docs"
if docs.exists():
    app.mount("/handbook", StaticFiles(directory=str(docs), html=True), name="handbook")
