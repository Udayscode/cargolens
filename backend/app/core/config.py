from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cargolens.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    storage_path: str = "./storage"
    gemini_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
