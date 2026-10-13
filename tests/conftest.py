import sys
import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = "./test_temp.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

os.environ["APP_ENV"] = "testing"
os.environ["ADMIN_API_KEY"] = "test_admin_secret_key"
os.environ["META_VERIFY_TOKEN"] = "test_verify_token"
os.environ["DATABASE_URL"] = TEST_DB_URL

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import Base, get_db
from app.main import app
from app.services.whatsapp import whatsapp_service

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Clean and create fresh tables for each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_whatsapp(monkeypatch):
    sent_messages = []

    async def mock_send(payload):
        sent_messages.append(payload)
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": payload.get("to"), "wa_id": payload.get("to")}],
            "messages": [{"id": f"wamid.test_{len(sent_messages)}"}]
        }

    monkeypatch.setattr(whatsapp_service, "_send_payload", mock_send)
    return sent_messages


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    # Cleanup temp file on exit
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
