from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, health, items, users, vendor

api_router = APIRouter()

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & JWT"])
api_router.include_router(users.router, prefix="/users", tags=["Users & IDOR"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin Command (RBAC)"])
api_router.include_router(
    vendor.router, prefix="/vendor", tags=["Ripperdoc Vendor Portal"]
)
api_router.include_router(
    items.router, prefix="/items", tags=["Catalog Modifications (MVP)"]
)
