from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import engine, init_db
from app.schemas import HealthCheck
from app.api import api_router


setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    database = "supabase" if settings.SUPABASE_DATABASE_URL else "sqlite"
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        database=database,
    )


@app.get("/db-test", tags=["health"])
async def db_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
    return {"database": "connected", "result": result}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
