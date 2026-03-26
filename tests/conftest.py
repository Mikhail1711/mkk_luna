import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from app.main import app
from app.models import Base
from app.database import get_db


load_dotenv()

TEST_DATABASE_URL = os.getenv("DATABASE_URL") + "_test"  # type: ignore
test_engine = create_async_engine(TEST_DATABASE_URL)
test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True, scope="session")
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def client():
    async def override_get_async_session():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_async_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        STATIC_API_KEY = os.getenv("STATIC_API_KEY")
        client.headers.update({"API-KEY": STATIC_API_KEY})  # type: ignore
        yield client

    app.dependency_overrides.clear()
