"""추천 파이프라인 진행 이벤트 — /recommendations/stream 이 머리 장면을 실제 진행에 묶는 데 쓴다.

emit(name, **fields) 는 현재 컨텍스트에 콜백이 있을 때만 호출한다(없으면 no-op — 비스트림 경로·잡은 비용 0).
ContextVar 라 submit_timed(copy_context) 로 넘어간 워커에서도 같은 콜백이 보인다.
"""

from contextvars import ContextVar
from typing import Any, Callable

_cb: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "progress_cb", default=None
)


def emit(type_: str, **fields: Any) -> None:
    cb = _cb.get()
    if cb is not None:
        cb({"type": type_, **fields})


def set_callback(cb: Callable[[dict[str, Any]], None] | None):
    """토큰을 돌려준다 — 끝나면 reset(token)."""
    return _cb.set(cb)


def reset(token) -> None:
    _cb.reset(token)


if __name__ == "__main__":
    got: list[dict] = []
    emit("stage", stage="search", candidates=3)  # 콜백 없음 → 아무 일 없음
    assert got == []
    tok = set_callback(got.append)
    emit("funnel", total=10, industry=2)
    emit("stage", stage="qualify", passed=1)
    reset(tok)
    emit("stage", stage="rank", results=1)
    assert got == [
        {"type": "funnel", "total": 10, "industry": 2},
        {"type": "stage", "stage": "qualify", "passed": 1},
    ], got
    print("ok progress: no-op without callback · emits with callback · reset stops")
