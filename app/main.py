import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader

from app.models import Base
from app.database import engine


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
