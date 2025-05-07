# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router_v1
from app.db import base_class # Import Base to create tables (not strictly needed if using Alembic for creation)
# from app.services.redis_service import redis_client, close_redis_connection # If Redis client needs explicit start/stop

# base_class.Base.metadata.create_all(bind=engine) # This would create tables, but Alembic should handle it.

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# @app.on_event("startup")
# async def startup_event():
#     # Initialize Redis client if needed
#     # await redis_client.init_redis_pool() # Example if redis_client has such a method
#     # Create initial superuser if not exists (can be a script or a CLI command)
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     # Close Redis connection pool
#     # await close_redis_connection()
#     pass

app.include_router(api_router_v1, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Bem-vindo à API {settings.PROJECT_NAME}! Acesse /docs para a documentação da API V1."}

# For running directly with uvicorn for development:
# uvicorn app.main:app --reload --port 8000

