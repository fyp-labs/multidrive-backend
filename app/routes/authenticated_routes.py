from fastapi import APIRouter
from app.routes import google_drive_routes

router = APIRouter()

router.include_router(google_drive_routes.router, prefix="/google/drive")

