from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


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
