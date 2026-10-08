from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CREDENTIALS_PATH = DATA_DIR / "google.json"
CLASSIFICATION_CACHE_PATH = DATA_DIR / "classifications.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    broom_host: str = "127.0.0.1"
    broom_port: int = 8000
    laya_model: str = "aac6fef/laya-mlx"
    frontend_origin: str = "http://127.0.0.1:5173"
    oauth_redirect_path: str = "/api/auth/callback"

    @property
    def redirect_uri(self) -> str:
        return f"http://{self.broom_host}:{self.broom_port}{self.oauth_redirect_path}"


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
