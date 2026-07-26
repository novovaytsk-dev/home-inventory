import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

# Явно импортируем все модели, чтобы их таблицы попали в metadata
from app.models.user import User
from app.models.product import Product
from app.models.batch import Batch
from app.models.operation import Operation
from app.models.notification import Notification
from app.models.shopping_list import ShoppingListItem

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "stock@test.com",
        "password": "test"
    })
    login_res = await client.post("/auth/login", data={
        "username": "stock@test.com",
        "password": "test"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}