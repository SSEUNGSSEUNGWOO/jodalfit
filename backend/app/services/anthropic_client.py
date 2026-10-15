"""Anthropic 클라이언트 — 첨부문서 인사이트(summarize_bid_documents). 임베딩은 계속 OpenAI."""
from functools import lru_cache

import anthropic

from app.core.config import get_settings


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다 (backend/.env)")
    return anthropic.Anthropic(api_key=key)
