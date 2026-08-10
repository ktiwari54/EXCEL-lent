from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EXCEL-lent Data Analyst Engine"
    app_version: str = "0.1.0"
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 50
    session_ttl_hours: int = 24

    base_dir: Path = Path(__file__).resolve().parent.parent
    uploads_dir: Path = base_dir / "uploads"
    exports_dir: Path = base_dir / "exports"
    sessions_dir: Path = base_dir / "data" / "sessions"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    return settings
