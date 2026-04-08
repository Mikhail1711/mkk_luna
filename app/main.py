import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from loguru import logger

from app.models import Base
from app.database import engine
from app.api import router as orgs_router


logger.add(
    "logs/activity.log",
    level="INFO",
    filter=lambda record: record["level"].no < 40,
    rotation="10 MB",
)

logger.add(
    "logs/error.log",
    rotation="10 MB",
    retention="100 days",
    compression="zip",
    level="ERROR",
)

STATIC_KEY = os.getenv("STATIC_API_KEY")
api_key_header = APIKeyHeader(name="API-KEY", auto_error=True)


def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == STATIC_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Неверный ключ")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(get_api_key)],
    title="MKK Luna API",
    description="API справочника организаций",
)

app.include_router(orgs_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Непредвиденная ошибка при запросе к {request.url.path}")

    return JSONResponse(
        status_code=500,
        content={"message": "Что-то пошло не так на сервере"},
    )
