"""
Configurações do SaaS Backend
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


# Caminho absoluto para o banco na raiz do projeto (D:/Front_Bier/bierpass.db)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "bierpass.db"


class Settings(BaseSettings):
    # Database (fixo e absoluto para evitar múltiplos arquivos em cwd diferentes)
    database_url: str = f"sqlite:///{DATABASE_PATH}"
    
    # Auth
    secret_key: str = "BIERPASS_DEV_SECRET_KEY_CHANGE_IN_PRODUCTION_2025"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 horas
    
    # App
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    
    # CORS - Origens permitidas
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "file://",  # Para APP local
    ]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
