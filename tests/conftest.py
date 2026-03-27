import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import pytest
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

from app.main import app
from app.models import Base
from app.database import get_db


load_dotenv()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    ADMIN_URL = os.getenv("ADMIN_URL")
    admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")  # type: ignore
    async with admin_engine.connect() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS organizations_db_test"))
        await conn.execute(text("CREATE DATABASE organizations_db_test"))
    await admin_engine.dispose()


@pytest.fixture(scope="session")
async def test_engine_fixture(setup_test_db):
    TEST_DATABASE_URL = os.getenv("DATABASE_URL") + "_test"  # type: ignore
    test_engine = create_async_engine(TEST_DATABASE_URL)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(scope="session")
async def client(test_engine_fixture):
    test_session_maker = async_sessionmaker(test_engine_fixture, expire_on_commit=False)

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
