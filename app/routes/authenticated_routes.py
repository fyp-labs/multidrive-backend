from fastapi import APIRouter
from app.routes import google_drive_routes
from app.routes import one_drive_routes

router = APIRouter()

router.include_router(google_drive_routes.router, prefix="/google/drive")
router.include_router(one_drive_routes.router, prefix="/one/drive")


