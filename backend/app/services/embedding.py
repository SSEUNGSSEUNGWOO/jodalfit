"""임베딩 공간 스위치 — openai(1536d) / kure(1024d) / gemini(768d). 모든 호출부는 이 모듈만 쓴다.

공간마다 (열, 시각 열, RPC 접미사, 임베딩 함수)가 한 벌이다. 전환은 `EMBED_SPACE` 하나(0045 kure, 0067 gemini).
gemini 는 질의/문서 taskType 이 다르다 — 업종 텍스트·키워드 질의는 kind="query", 공고·사전규격·발주계획은 "document".
다른 공간은 kind 를 무시한다.
"""

from __future__ import annotations

import hashlib
from typing import Callable

from app.core.config import get_settings

SPACES = {
    #            차원   벡터 열          시각 열           RPC 접미사
    "openai": (1536, "embedding", "embedded_at", ""),
    "kure": (1024, "embedding_k", "embedded_k_at", "_k"),
    "gemini": (768, "embedding_g", "embedded_g_at", "_g"),
}
CACHE_TABLE = "text_embeddings"
CACHE_COL = {"kure": "embedding", "gemini": "embedding_g"}  # 0046 표는 vector(1024) 고정이라 gemini 는 별도 열(0067)
CACHE_LOOKUP_CHUNK = 150  # PostgREST URL 길이 ~7KB 안전선 — compute_company_vectors EMB_PAGE 와 같은 근거


def _space(space: str | None) -> str:
    return space or get_settings().embed_space


def dim(space: str | None = None) -> int:
    return SPACES[_space(space)][0]


def emb_col(space: str | None = None) -> str:
    """벡터 컬럼 이름. recommend.py::_emb_col 과 같은 규칙."""
    return SPACES[_space(space)][1]


def at_col(space: str | None = None) -> str:
    """임베딩 시각 컬럼 — 잡이 '아직 안 한 행' 을 고를 때 본다."""
    return SPACES[_space(space)][2]


def rpc_name(base: str, space: str | None = None) -> str:
    """공간에 맞는 RPC 이름 (match_bid_notices → match_bid_notices_k / _g)."""
    return base + SPACES[_space(space)][3]


def embed_texts(texts: list[str], space: str | None = None, kind: str = "document") -> list[list[float]]:
    s = _space(space)
    if s == "kure":
        from app.services.local_embed import embed_texts_kure

        return embed_texts_kure(texts)
    if s == "gemini":
        from app.services.gemini_client import embed_texts as _gemini_embed

        return _gemini_embed(texts, kind)
    from app.services.openai_client import embed_texts as _openai_embed

    return _openai_embed(texts)


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _cached(
    texts: list[str],
    lookup: Callable[[list[str]], dict[str, list[float]]],
    store: Callable[[dict[str, list[float]]], None],
    embed: Callable[[list[str]], list[list[float]]],
) -> list[list[float]]:
    """sha1 캐시 조회 → 미스만 embed → 저장 → 입력 순서대로 반환.

    DB 접근을 주입받는 순수 로직 — `__main__` 자체 점검이 스텁으로 이 부분만 확인한다.
    """
    shas = [_sha1(t) for t in texts]
    by_sha = dict(zip(shas, texts))  # 같은 텍스트 중복은 한 번만 임베딩
    hits: dict[str, list[float]] = {}
    uniq = list(by_sha)
    for i in range(0, len(uniq), CACHE_LOOKUP_CHUNK):
        hits.update(lookup(uniq[i : i + CACHE_LOOKUP_CHUNK]))
    misses = [s for s in uniq if s not in hits]
    if misses:
        fresh = dict(zip(misses, embed([by_sha[s] for s in misses])))
        fresh_items = list(fresh.items())
        for i in range(0, len(fresh_items), CACHE_LOOKUP_CHUNK):
            store(dict(fresh_items[i : i + CACHE_LOOKUP_CHUNK]))
        hits.update(fresh)
    return [hits[s] for s in shas]


def _parse_vector(v: str | list) -> list[float]:
    """PostgREST 는 vector 컬럼을 '[0.1,0.2,...]' 문자열로 돌려준다."""
    if isinstance(v, list):
        return [float(x) for x in v]
    return [float(x) for x in v.strip()[1:-1].split(",")]


def embed_texts_cached(texts: list[str], space: str | None = None, kind: str = "document") -> list[list[float]]:
    """같은 텍스트를 두 번 임베딩하지 않는다 (kure·gemini — 0046 text_embeddings, gemini 열은 0067).

    openai 는 API 가 싸고 빨라서 캐시 가치가 없다 → 그대로 통과.
    테이블이 없으면 PostgREST 에러를 그대로 올린다 — 조용히 건너뛰면 Actions 가
    업종 텍스트 2.5만 건을 매일 CPU 로 다시 임베딩하며 timeout 날 때까지 모른다.
    캐시 키는 (space, sha1) 뿐이다 — 질의와 문서가 같은 글일 일이 없어 kind 는 키에 넣지 않는다.
    """
    space = _space(space)
    col = CACHE_COL.get(space)
    if col is None or not texts:
        return embed_texts(texts, space, kind) if texts else []

    from app.services.openai_client import vector_to_pgvector_str
    from app.services.supabase_client import get_admin_client

    client = get_admin_client()

    def lookup(shas: list[str]) -> dict[str, list[float]]:
        rows = (
            client.table(CACHE_TABLE)
            .select(f"text_sha1,vec:{col}")
            .eq("space", space)
            .in_("text_sha1", shas)
            .not_.is_(col, "null")
            .execute()
            .data
        )
        return {r["text_sha1"]: _parse_vector(r["vec"]) for r in rows}

    def store(fresh: dict[str, list[float]]) -> None:
        client.table(CACHE_TABLE).upsert(
            [
                {"space": space, "text_sha1": s, col: vector_to_pgvector_str(e)}
                for s, e in fresh.items()
            ]
        ).execute()

    return _cached(texts, lookup, store, lambda t: embed_texts(t, space, kind))


if __name__ == "__main__":
    # sha1 키 + 입력 순서 복원 자체 점검 (DB·모델 없이 스텁으로).
    store_db: dict[str, list[float]] = {}
    calls: list[list[str]] = []

    def fake_embed(ts: list[str]) -> list[list[float]]:
        calls.append(ts)
        return [[float(len(t))] for t in ts]

    texts = ["가", "나", "가", "다"]
    store_db[_sha1("나")] = [99.0]  # 미리 캐시된 항목
    out = _cached(
        texts,
        lambda shas: {s: store_db[s] for s in shas if s in store_db},
        lambda fresh: store_db.update(fresh),
        fake_embed,
    )
    assert out == [[1.0], [99.0], [1.0], [1.0]], out
    assert calls == [["가", "다"]], calls  # 캐시 히트·중복은 모델 호출 안 함
    out2 = _cached(texts, lambda shas: {s: store_db[s] for s in shas if s in store_db},
                   lambda fresh: store_db.update(fresh), fake_embed)
    assert out2 == out and len(calls) == 1, (out2, calls)  # 두 번째는 전부 캐시
    assert (dim("gemini"), emb_col("gemini"), at_col("gemini"), rpc_name("match_bid_notices", "gemini")) == (768, "embedding_g", "embedded_g_at", "match_bid_notices_g")
    assert rpc_name("match_bid_notices", "openai") == "match_bid_notices" and emb_col("kure") == "embedding_k"
    print("embed_texts_cached 자체 점검 OK (sha1 키, 순서 복원, 중복/히트 생략, 공간 표)")
