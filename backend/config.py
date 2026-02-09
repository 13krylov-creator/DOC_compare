import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "DocumentCompare Platform"
    APP_VERSION: str = "2.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 5055
    
    # Database
    DATABASE_URL: str = "sqlite:///./doccompare.db"
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "doccompare-secret-key-2026-very-secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Keycloak OIDC Settings
    KEYCLOAK_SERVER_URL: str = os.getenv("KEYCLOAK_SERVER_URL", "https://auth.nir.center")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "platform")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "oauth2-proxy")
    KEYCLOAK_CLIENT_SECRET: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "mZsGFiHJG59MH0rrOVPlgtdtBHH9zf3d")
    
    # ML Services
    ML_HOST_GPT: str = os.getenv("ML_HOST_GPT", "10.109.50.250:1212")
    ML_MODEL_GPT: str = os.getenv("ML_MODEL_GPT", "openai/gpt-oss-20b")
    ML_HOST_VISION: str = os.getenv("ML_HOST_VISION", "10.109.50.250:8880")
    ML_MODEL_VISION: str = os.getenv("ML_MODEL_VISION", "/model")
    ML_TIMEOUT: int = int(os.getenv("ML_TIMEOUT", "120"))
    
    # File storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "txt"]
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create upload directory if not exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# ML Configuration (as specified in requirements)
ML_CONFIG = {
    "gpt": {
        "host": settings.ML_HOST_GPT,
        "model": settings.ML_MODEL_GPT,
    },
    "vision": {
        "host": settings.ML_HOST_VISION,
        "model": settings.ML_MODEL_VISION,
    },
    "timeout": settings.ML_TIMEOUT,
}
