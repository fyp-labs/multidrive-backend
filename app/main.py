from fastapi import FastAPI
from app.config.lifespan import lifespan
from app.routes import authenticated_routes

app = FastAPI(lifespan=lifespan)

app.include_router(authenticated_routes.router, prefix="/authenticated")