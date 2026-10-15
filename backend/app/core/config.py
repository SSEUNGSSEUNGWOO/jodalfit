from functools import lru_cache
from typing import Literal

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

    # Sentry — 비우면 비활성.
    sentry_dsn: str | None = None

    # Anthropic — 첨부문서 인사이트(Haiku). 비우면 openai 로 degrade 하지 않고 잡이 명시적으로 실패한다.
    anthropic_api_key: str | None = None
    # 첨부문서 인사이트 공급자. anthropic(Haiku 4.5, 2026-10-15 비교 37:3) / openai(gpt-4o-mini, 롤백용)
    insight_provider: Literal["openai", "anthropic"] = "anthropic"

    # 추천 후보 검색 방식 — dense(벡터 1채널) / hybrid(dense + 업종 허용 공고 채널, 0044 필요).
    # 근거: docs/recommender/exp-2026-10-14-retrieval.md. 문제 시 dense 로 즉시 롤백.
    reco_retrieval: Literal["dense", "hybrid"] = "hybrid"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
