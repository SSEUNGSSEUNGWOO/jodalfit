"""임베딩 공간 스위치 — openai(1536d) / kure(1024d). 모든 호출부는 이 모듈만 쓴다."""

from __future__ import annotations

from app.core.config import get_settings

DIMS = {"openai": 1536, "kure": 1024}


def dim(space: str | None = None) -> int:
    return DIMS[space or get_settings().embed_space]


def embed_texts(texts: list[str], space: str | None = None) -> list[list[float]]:
    if (space or get_settings().embed_space) == "kure":
        from app.services.local_embed import embed_texts_kure

        return embed_texts_kure(texts)
    from app.services.openai_client import embed_texts as _openai_embed

    return _openai_embed(texts)
