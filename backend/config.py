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
    KEYCLOAK_CLIENT_SECRET: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "oauth2_proxy_secret_change_me")
    
    # ML Services
    ML_HOST_GPT: str = os.getenv("ML_HOST_GPT", "10.109.50.250:1212")
    ML_MODEL_GPT: str = os.getenv("ML_MODEL_GPT", "Qwen3-VL")
    ML_HOST_VISION: str = os.getenv("ML_HOST_VISION", "10.109.50.250:8880")
    ML_MODEL_VISION: str = os.getenv("ML_MODEL_VISION", "/model")
    ML_TIMEOUT: int = int(os.getenv("ML_TIMEOUT", "120"))
    
    # File storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "txt"]
    FILE_RETENTION_DAYS: int = int(os.getenv("FILE_RETENTION_DAYS", "7"))  # Files auto-delete after 7 days
    
    # Anonymizer settings
    ANONYMIZER_UPLOAD_DIR: str = os.getenv("ANONYMIZER_UPLOAD_DIR", "./anonymizer_uploads")
    ANONYMIZER_RETENTION_HOURS: int = int(os.getenv("ANONYMIZER_RETENTION_HOURS", "24"))
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create upload directory if not exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.ANONYMIZER_UPLOAD_DIR, exist_ok=True)

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

# ===================== Anonymizer Configuration =====================

from pathlib import Path

ANONYMIZER_UPLOAD_DIR = Path(settings.ANONYMIZER_UPLOAD_DIR)
ANONYMIZER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ANONYMIZER_SUPPORTED_FORMATS = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
}

ANONYMIZATION_OPTIONS = [
    {"id": "prices", "label": "Цены и суммы", "description": "Замена денежных значений"},
    {"id": "companies", "label": "Названия компаний", "description": "Замена названий организаций"},
    {"id": "logos", "label": "Логотипы", "description": "Удаление изображений логотипов"},
    {"id": "personal", "label": "ФИО и контакты", "description": "Замена персональных данных"},
    {"id": "addresses", "label": "Адреса и геолокация", "description": "Удаление физических адресов"},
    {"id": "requisites", "label": "Реквизиты", "description": "Удаление ИНН, ОГРН, счетов"},
    {"id": "dates", "label": "Даты и сроки", "description": "Замена абсолютных дат"},
    {"id": "technical", "label": "Технические детали", "description": "Замена продуктов и версий"},
    {"id": "metadata", "label": "Метаданные файлов", "description": "Очистка служебной информации"},
    {"id": "watermarks", "label": "Водяные знаки и подписи", "description": "Удаление визуальных идентификаторов"},
]

DEFAULT_PROFILES = {
    "full": {
        "name": "Полное обезличивание",
        "description": "Для конкурентов - все галочки включены",
        "options": ["prices", "companies", "logos", "personal", "addresses", "requisites", "dates", "technical", "metadata", "watermarks"],
    },
    "media": {
        "name": "Для СМИ",
        "description": "Оставить даты, убрать компании и цены",
        "options": ["prices", "companies", "logos", "personal", "addresses", "requisites", "technical", "metadata", "watermarks"],
    },
    "partners": {
        "name": "Для партнеров",
        "description": "Убрать только цены и реквизиты",
        "options": ["prices", "requisites", "metadata"],
    },
}
