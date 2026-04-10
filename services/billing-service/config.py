from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://sreesaaj:SreeSaaj%402024@postgres-billing:5432/billing_db"
    SECRET_KEY: str = "sreesaaj-super-secret-key-2024-production"
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80"

    class Config:
        env_file = ".env"


settings = Settings()
