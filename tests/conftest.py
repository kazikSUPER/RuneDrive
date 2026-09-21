import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.item import Item, ItemCategory
from app.models.user import User, UserRole

TEST_DB_FILE = "./test_runedrive.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Синхронна ініціалізація та очищення тестової БД SQLite."""

    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def _cleanup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            with contextlib.suppress(OSError):
                os.remove(TEST_DB_FILE)

    asyncio.run(_init())
    yield
    asyncio.run(_cleanup())


@pytest.fixture
def client():
    """Тестовий клієнт FastAPI."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seed_users():
    """Створення тестових облікових записів та товару для перевірки RBAC та IDOR."""

    async def _seed():
        async with TestingSessionLocal() as db_session:
            admin = User(
                username="netrunner_admin",
                email="admin@runedrive.net",
                hashed_password=get_password_hash("AdminSecret2026!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            buyer1 = User(
                username="street_samurai",
                email="samurai@runedrive.net",
                hashed_password=get_password_hash("SamuraiPass123!"),
                role=UserRole.BUYER,
                is_active=True,
            )
            buyer2 = User(
                username="cyber_mage",
                email="mage@runedrive.net",
                hashed_password=get_password_hash("MagePass123!"),
                role=UserRole.BUYER,
                is_active=True,
            )
            ripperdoc1 = User(
                username="dr_viktor",
                email="viktor@watson-clinic.net",
                hashed_password=get_password_hash("ViktorRipperPass1!"),
                role=UserRole.RIPPERDOC,
                is_active=True,
            )
            ripperdoc2 = User(
                username="fingers_md",
                email="fingers@jig-jig.net",
                hashed_password=get_password_hash("FingersPass123!"),
                role=UserRole.RIPPERDOC,
                is_active=True,
            )

            db_session.add_all([admin, buyer1, buyer2, ripperdoc1, ripperdoc2])
            await db_session.commit()
            await db_session.refresh(admin)
            await db_session.refresh(buyer1)
            await db_session.refresh(buyer2)
            await db_session.refresh(ripperdoc1)
            await db_session.refresh(ripperdoc2)

            item1 = Item(
                title="Очний імплант «Кіроші Mk.3»",
                slug="kiroshi-optics-mk3",
                category=ItemCategory.IMPLANT,
                price=1500.00,
                stock_quantity=10,
                is_active=True,
                specs={"zoom": "8x", "scan_speed": "0.2s"},
                owner_id=ripperdoc1.id,
            )
            db_session.add(item1)
            await db_session.commit()
            await db_session.refresh(item1)

            return {
                "admin": admin,
                "admin_token": create_access_token(admin.id, admin.role),
                "buyer1": buyer1,
                "buyer1_token": create_access_token(buyer1.id, buyer1.role),
                "buyer2": buyer2,
                "buyer2_token": create_access_token(buyer2.id, buyer2.role),
                "ripperdoc1": ripperdoc1,
                "ripperdoc1_token": create_access_token(ripperdoc1.id, ripperdoc1.role),
                "ripperdoc2": ripperdoc2,
                "ripperdoc2_token": create_access_token(ripperdoc2.id, ripperdoc2.role),
                "item1": item1,
            }

    return asyncio.run(_seed())
