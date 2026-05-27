from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    narajangteo_api_key: str
    openai_api_key: str
    supabase_url: str
    supabase_service_role_key: str

    cors_origins: list[str] = ["http://localhost:3000"]

    # 봇/스크래퍼 차단 — bot_guard.py 참고. 미설정 시 가드 비활성(개발 편의).
    internal_api_token: str | None = None
    allowed_referer_hosts: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
