from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://sreesaaj:SreeSaaj%402024@postgres-gallery:5432/gallery_db"
    SECRET_KEY: str = "sreesaaj-super-secret-key-2024-production"
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80"
    UPLOAD_DIR: str = "/app/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
