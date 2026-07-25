from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost/db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    expiring_soon_days: int = 3  # порог по умолчанию

    class Config:
        env_file = ".env"

settings = Settings()