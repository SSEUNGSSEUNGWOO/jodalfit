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
    # 추천 설명(explain.py) 공급자. anthropic(Haiku 4.5: 5건 병렬 2.3s vs 3.3s, 구체 인용 더 많음) / openai(gpt-4o-mini).
    # anthropic 인데 키가 없으면 openai 로 degrade (Railway 에 ANTHROPIC_API_KEY 넣기 전에도 배포 가능).
    explain_provider: Literal["openai", "anthropic"] = "anthropic"

    # 추천 후보 검색 방식 — dense(벡터 1채널) / hybrid(dense + 업종 허용 공고 채널, 0044 필요).
    # 근거: docs/recommender/exp-2026-10-14-retrieval.md. 문제 시 dense 로 즉시 롤백.
    reco_retrieval: Literal["dense", "hybrid"] = "hybrid"

    # 임베딩 공간 — openai(text-embedding-3-small 1536d, `embedding` 컬럼) /
    # kure(KURE-v1 1024d, `embedding_k` 컬럼). 근거: docs/recommender/exp-2026-10-15-embedding-model.md.
    # 전환은 환경변수 하나, 롤백도 하나. 컬럼·RPC 가 준비될 때까지 기본 openai.
    embed_space: Literal["openai", "kure"] = "openai"
    # KURE ONNX 모델 캐시 폴더. 미설정 시 임시 폴더(Railway 는 재시작마다 재다운로드 ~409MB).
    kure_model_dir: str | None = None

    # /feedback 알림 메일 — Resend API 키(Sending access). 비우면 DB 저장만 하고 메일은 안 보낸다.
    # 발신 noreply@jodalfit.co.kr 은 Supabase SMTP 와 같은 Resend 도메인(DKIM 인증 완료).
    resend_api_key: str | None = None
    feedback_notify_to: str = "jansseung@gmail.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
