import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from temporalio.client import Client
from sqlalchemy import text
from app.config.database import engine  

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check DB connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(" Database connected successfully")
    except Exception as e:
        print(" Database connection failed:", e)
        raise

    # Connect Temporal
    app.state.temporal_client = await Client.connect(os.getenv("TEMPORAL_CLIENT"))
    print(" Temporal client connected")

    yield  

    # Close Temporal
    temporal_client = app.state.temporal_client
    if temporal_client:
        await temporal_client.close()
    print(" Temporal client disconnected")

    # Dispose DB connections
    engine.dispose()
    print(" Database engine disposed")


app = FastAPI(lifespan=lifespan)
