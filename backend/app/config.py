"""Application configuration."""

from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    openai_api_key: str = "sk-xxx"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # Database
    database_url: str = "sqlite+aiosqlite:///./aipm.db"

    # Auth
    jwt_secret: str = "CHANGE-ME-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # App
    app_env: str = "development"
    debug: bool = True

    # CORS — accepts comma-separated string from env var
    cors_origins: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.cors_origins, str):
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return self.cors_origins


settings = Settings()
