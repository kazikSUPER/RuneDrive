from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


async def seed_initial_data():
    """Створення початкових демонстраційних користувачів та товарів, якщо вони відсутні."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.item import Item, ItemCategory
    from app.models.user import User, UserRole

    async with AsyncSessionLocal() as session:
        admin_res = await session.execute(
            select(User).where(User.username == "netrunner_admin")
        )
        if not admin_res.scalar_one_or_none():
            admin = User(
                username="netrunner_admin",
                email="admin@runedrive.net",
                hashed_password=get_password_hash("AdminSecret2026!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            ripperdoc = User(
                username="dr_viktor",
                email="viktor@watson-clinic.net",
                hashed_password=get_password_hash("ViktorRipperPass1!"),
                role=UserRole.RIPPERDOC,
                is_active=True,
            )
            buyer = User(
                username="street_samurai",
                email="samurai@runedrive.net",
                hashed_password=get_password_hash("SamuraiPass123!"),
                role=UserRole.BUYER,
                is_active=True,
            )
            session.add_all([admin, ripperdoc, buyer])
            await session.flush()

            item1 = Item(
                title="Очний імплант «Кіроші Mk.3»",
                slug="kiroshi-optics-mk3",
                category=ItemCategory.IMPLANT,
                price=1500.00,
                stock_quantity=10,
                is_active=True,
                specs={"zoom": "8x", "scan_speed": "0.2s"},
                owner_id=ripperdoc.id,
            )
            item2 = Item(
                title="Цифрова руна «Прошивка перевантаження»",
                slug="overload-firmware-v2",
                category=ItemCategory.SOFTWARE,
                price=450.00,
                stock_quantity=50,
                is_active=True,
                specs={"firmware": "2.4.1", "damage_boost": "+15%"},
                owner_id=ripperdoc.id,
            )
            session.add_all([item1, item2])
            await session.commit()
            print("[*] Initial demo users and items seeded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Асинхронний життєвий цикл застосунку (Startup / Shutdown події)."""
    print(f"[*] {settings.PROJECT_NAME} starting up on v{settings.VERSION}...")
    try:
        import app.models  # noqa: F401
        from app.core.database import Base, engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[*] Database tables verified / created successfully.")

        try:
            await seed_initial_data()
        except Exception as seed_err:
            print(f"[!] Info: Seeding skipped or deferred ({seed_err}).")
    except Exception as e:
        print(
            f"[!] Info: Database not initialized yet ({e}). Healthchecks will report status."
        )

    yield

    print(f"[*] {settings.PROJECT_NAME} shutting down...")
    from app.core.database import engine

    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root_redirect(request: Request):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "ui": "/ui",
    }


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui_page():
    if INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>RuneDrive UI</h1><p>index.html not found</p>")
