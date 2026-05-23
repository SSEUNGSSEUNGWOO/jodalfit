"""OpenAI 클라이언트 wrapper - 임베딩 + 채팅."""

from __future__ import annotations

import time
from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings


@lru_cache
def get_openai_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되지 않았습니다.")
    return OpenAI(api_key=settings.openai_api_key)


EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
MAX_BATCH = 100


def embed_texts(texts: list[str], max_retries: int = 3) -> list[list[float]]:
    """배치 임베딩. 빈 입력은 zero 벡터로 채움.

    OpenAI는 한 호출에 다수 입력 가능하지만 안정성 위해 100건씩 끊음.
    """
    if not texts:
        return []
    client = get_openai_client()
    out: list[list[float]] = []
    for i in range(0, len(texts), MAX_BATCH):
        batch = texts[i : i + MAX_BATCH]
        # 빈/공백 입력은 OpenAI가 reject — 임시 placeholder로 바꾸고 결과는 zero
        cleaned = [t.strip() or "(empty)" for t in batch]
        for attempt in range(max_retries):
            try:
                resp = client.embeddings.create(input=cleaned, model=EMBED_MODEL)
                out.extend([d.embedding for d in resp.data])
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                print(f"  embed retry {attempt + 1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
    return out


def vector_to_pgvector_str(vec: list[float]) -> str:
    """pgvector 컬럼 입력 형식 '[1.0, 2.0, ...]'."""
    return "[" + ",".join(f"{v:.7f}" for v in vec) + "]"
