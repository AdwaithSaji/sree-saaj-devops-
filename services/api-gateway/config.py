from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    EVENT_SERVICE_URL: str = "http://event-service:8002"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8003"
    BILLING_SERVICE_URL: str = "http://billing-service:8004"
    GALLERY_SERVICE_URL: str = "http://gallery-service:8005"
    MENU_SERVICE_URL: str = "http://menu-service:8006"
    SECRET_KEY: str = "sreesaaj-super-secret-key-2024-production"
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80,http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
