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

    # IP 해시 솔트 — search_log.py의 ip_hash 사전계산 방어. 미설정 시 빈 솔트(약함).
    ip_hash_salt: str | None = None

    # FastAPI /docs, /redoc 활성 여부 — 운영에서는 false 권장.
    enable_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
