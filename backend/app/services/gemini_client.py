"""Google gemini-embedding-001 임베딩 — REST batchEmbedContents, 768d(MRL), 질의/문서 taskType 분리.

실험(docs/recommender/exp-2026-11-04-embedding-rematch.md)에서 쓴 호출 그대로다:
- 공고·사전규격·발주계획 = RETRIEVAL_DOCUMENT, 업종 텍스트·키워드 질의 = RETRIEVAL_QUERY. 같게 넣으면 −0.043.
- outputDimensionality 768 은 3072 대비 손실 없음(0.580 vs 0.576). MRL 축소 벡터는 단위 길이가 아니라 L2 정규화한다.
- 요청당 100건. 유료 등급 기준. 429·5xx·네트워크 오류는 지수 백오프로 재시도.

차단기: 연속 실패가 나면 `BREAK_SECONDS` 동안 호출 없이 바로 `GeminiUnavailable` 을 올린다 —
구글 장애 때 요청마다 타임아웃을 기다리다 추천 전체가 느려지는 걸 막는다. 호출부(키워드 모드)는 이걸 받아
제목 일치만 돌려준다. 회사 모드는 저장된 벡터를 쓰므로 이 모듈을 거치지 않는다.
"""

from __future__ import annotations

import logging
import math
import threading
import time

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-001"
DIM = 768
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents"
BATCH = 100
MAX_CHARS = 6000  # 실험과 동일. 공고 텍스트 평균 82자라 거의 안 잘린다
TASK = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}
BREAK_SECONDS = 60.0
BREAK_AFTER_FAILURES = 2

_lock = threading.Lock()
_failures = 0
_open_until = 0.0


class GeminiUnavailable(RuntimeError):
    """차단기가 열려 있거나 재시도를 다 써서 임베딩을 못 받았다."""


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 0 else v


def _record(ok: bool) -> None:
    global _failures, _open_until
    with _lock:
        if ok:
            _failures = 0
            return
        _failures += 1
        if _failures >= BREAK_AFTER_FAILURES:
            _open_until = time.monotonic() + BREAK_SECONDS
            logger.warning("gemini 차단기 열림 — %.0f초 동안 호출 생략", BREAK_SECONDS)


def breaker_open() -> bool:
    return time.monotonic() < _open_until


def embed_texts(
    texts: list[str],
    kind: str = "document",
    *,
    timeout: float = 20.0,
    max_retries: int = 4,
) -> list[list[float]]:
    """배치 임베딩. 빈 입력은 zero 벡터. kind = document | query."""
    if not texts:
        return []
    if breaker_open():
        raise GeminiUnavailable("gemini 차단기 열림")
    key = get_settings().gemini_api_key
    if not key:
        raise GeminiUnavailable("GEMINI_API_KEY 미설정")
    task = TASK[kind]
    out: list[list[float]] = [[0.0] * DIM] * len(texts)
    todo = [(i, t.strip()[:MAX_CHARS]) for i, t in enumerate(texts) if t and t.strip()]
    with httpx.Client(timeout=timeout) as c:
        for s in range(0, len(todo), BATCH):
            chunk = todo[s : s + BATCH]
            body = {
                "requests": [
                    {"model": f"models/{MODEL}", "content": {"parts": [{"text": t}]},
                     "taskType": task, "outputDimensionality": DIM}
                    for _, t in chunk
                ]
            }
            last = ""
            for attempt in range(max_retries + 1):
                try:
                    r = c.post(URL, params={"key": key}, json=body)
                except httpx.HTTPError as e:
                    last = f"network: {e}"
                else:
                    if r.status_code == 200:
                        vecs = [e["values"] for e in r.json()["embeddings"]]
                        if len(vecs) != len(chunk):
                            raise RuntimeError(f"gemini 응답 수 불일치 {len(vecs)} != {len(chunk)}")
                        for (i, _), v in zip(chunk, vecs):
                            out[i] = _normalize(v)
                        _record(True)
                        break
                    last = f"{r.status_code}: {r.text[:200]}"
                    if r.status_code not in (429, 500, 502, 503, 504):
                        _record(False)
                        raise RuntimeError(f"gemini 임베딩 실패 {last}")
                if attempt == max_retries:
                    _record(False)
                    raise GeminiUnavailable(f"gemini 임베딩 재시도 소진 — {last}")
                time.sleep(min(30.0, 2.0 * (2**attempt)))
    return out


if __name__ == "__main__":
    # 차단기 자체 점검 (네트워크 없이)
    _record(False); assert not breaker_open()
    _record(False); assert breaker_open()
    _record(True); assert _failures == 0 and breaker_open()  # 열린 창은 시간이 지나야 닫힌다
    assert _normalize([3.0, 4.0]) == [0.6, 0.8]
    print("gemini_client 자체 점검 OK (차단기 2회 실패 후 열림, 정규화)")
