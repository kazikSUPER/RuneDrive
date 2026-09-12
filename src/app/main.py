from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Асинхронний життєвий цикл застосунку (Startup / Shutdown події)."""
    print(f"[*] {settings.PROJECT_NAME} starting up on v{settings.VERSION}...")
    # Автоматичне створення таблиць для dev-середовища, якщо база доступна
    try:
        import app.models  # noqa: F401 - реєстрація моделей для Base.metadata
        from app.core.database import Base, engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[*] Database tables verified / created successfully.")
    except Exception as e:
        print(
            f"[!] Info: Database not initialized yet ({e}). Healthchecks will report status."
        )

    yield

    # Акуратне закриття пулу з'єднань при зупинці застосунку
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

# Налаштування CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключення роутів версії 1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
