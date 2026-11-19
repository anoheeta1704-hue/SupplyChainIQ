# ============================================
# SupplyChainIQ — Application Configuration
# ============================================
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    # App
    APP_NAME: str = "SupplyChainIQ"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://sciq_user:sciq_dev_password_2024@localhost:5432/supplychainiq"
    DATABASE_URL_SYNC: str = "postgresql://sciq_user:sciq_dev_password_2024@localhost:5432/supplychainiq"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8501"]'

    # AWS (optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "supplychainiq"

    # Local storage
    LOCAL_STORAGE_PATH: str = "./storage"

    # ML
    MODEL_PATH: str = "./ml_models"
    DELAY_THRESHOLD_LOW: float = 0.30
    DELAY_THRESHOLD_HIGH: float = 0.70

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()

