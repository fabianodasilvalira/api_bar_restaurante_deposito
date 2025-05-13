import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # Para servir arquivos estáticos se necessário

from app.core.config import settings
from app.api.v1.router import api_router_v1
from app.database import engine
from app.db import base_class  # Import Base para criação de tabelas

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API de gestão para restaurantes - Sistema completo para controle de mesas, comandas, pedidos e fiado",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION,
    contact={
        "name": "Suporte Técnico",
        "email": settings.SUPPORT_EMAIL,
    },
    license_info={
        "name": "MIT",
    },
)

# Configuração de CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Opcional: Criar tabelas automaticamente (em desenvolvimento)
# Em produção, use migrações com Alembic
if settings.ENVIRONMENT == "development":
    @app.on_event("startup")
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(base_class.Base.metadata.create_all)
        logger.info("Tabelas criadas com sucesso (apenas em desenvolvimento)")


# Inclui todas as rotas da API V1
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": f"Bem-vindo à API {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}",
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "operacional",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Endpoint para verificação de saúde da API"""
    return {
        "status": "healthy",
        "database": "connected" if settings.DATABASE_URL else "disconnected",
        "environment": settings.ENVIRONMENT
    }

