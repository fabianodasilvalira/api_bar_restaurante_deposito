from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "a_very_secret_key_that_should_be_in_env_var"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = "postgresql://restaurant_user:securepassword@localhost/restaurant_db"

    class Config:
        env_file = ".env"

settings = Settings()

