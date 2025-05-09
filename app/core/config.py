from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Configurações básicas do projeto
    PROJECT_NAME: str = "API Restaurante/Bar"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Configurações de segurança
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")

    # Configurações de token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(..., env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Configurações de banco de dados
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Configurações opcionais (com valores padrão)
    ENVIRONMENT: str = "development"
    SUPPORT_EMAIL: str = "support@example.com"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Configurações de CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignora variáveis extras não declaradas


settings = Settings()