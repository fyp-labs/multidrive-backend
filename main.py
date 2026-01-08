from fastapi import FastAPI
from app.config.lifespan import lifespan
from app.routes import authenticated_routes
import uvicorn

app = FastAPI(lifespan=lifespan)

app.include_router(authenticated_routes.router, prefix="/authenticated")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)