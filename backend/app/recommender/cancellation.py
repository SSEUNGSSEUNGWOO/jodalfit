"""취소공고 제외 — 취소된 (공고번호, 차수)를 후보에서 뺀다.

근거(2026-10-25 실측): 마감 90일 이내·벡터 있는 진행 중 공고 9,646행 중 920행(9.5%)이 취소공고이거나
그 뒤 차수에 취소공고가 붙은 원공고였고, 후보 검색 RPC 는 마감일만 보므로 전부 후보에 올라왔다
(유원디자인연구소 결과 11·13번이 같은 공사 — 13번은 취소된 원공고, 11번은 새 번호의 재발주).

신호는 목록 API 의 공고상태 bidNtceSttusNm(raw) 이 가장 넓다 — 최근 60일 취소공고 3,716행 중 제목에
'취소'가 있는 것은 124행뿐이다. 상태를 모르는 행(60일 66,673행 중 559행)만 제목으로 추측하되
'재공고·새로공고·재입찰'이 함께 있으면 새 공고로 본다("취소공고 및 새로공고"는 살아 있는 공고다).

차수 규칙: 취소공고 차수 이하는 전부 취소(원공고 000 + 취소공고 001). 그 뒤 차수는 산다.
운영(pipeline.rank_v2)과 하네스(jobs/evaluate_recommender.replay)가 같은 함수를 쓴다.
공고 상세 페이지·공고 목록·funnel_counts(0057)는 아직 이 판정을 모른다 — 수집 때 컬럼으로 두는 것이 다음 단계.
"""

from __future__ import annotations

REISSUE_WORDS = ("재공고", "새로공고", "재입찰")


def is_cancel_row(title: str | None, kind: str | None, status: str | None) -> bool:
    """공고 한 행(차수)이 취소공고인가. 상태·종류를 아는 행은 제목으로 추측하지 않는다."""
    if status or kind:
        return "취소" in (status or "") or "취소" in (kind or "")
    t = title or ""
    return "취소" in t and not any(w in t for w in REISSUE_WORDS)


def cancel_ords(rows: list[dict]) -> dict[str, str]:
    """{공고번호: 가장 큰 취소 차수}. rows 의 각 dict 는 bid_ntce_no, bid_ntce_ord, bid_ntce_nm, status, kind."""
    out: dict[str, str] = {}
    for r in rows:
        if is_cancel_row(r.get("bid_ntce_nm"), r.get("kind"), r.get("status")):
            no, od = r.get("bid_ntce_no") or "", r.get("bid_ntce_ord") or "000"
            if no and od >= out.get(no, ""):
                out[no] = od
    return out


def is_cancelled(no: str, ord_: str, cmap: dict[str, str]) -> bool:
    c = cmap.get(no)
    return c is not None and (ord_ or "000") <= c


def drop_cancelled(cands: list[dict], cmap: dict[str, str]) -> list[dict]:
    if not cmap:
        return cands
    return [r for r in cands if not is_cancelled(r.get("bid_ntce_no") or "", r.get("bid_ntce_ord") or "000", cmap)]


if __name__ == "__main__":   # uv run python -m app.recommender.cancellation
    assert is_cancel_row("아무 제목", None, "취소공고")
    assert is_cancel_row("아무 제목", "취소공고", "일반공고")
    assert not is_cancel_row("정비사업 취소공고 및 새로공고", None, "일반공고")   # 상태를 아는 행은 제목을 안 본다
    assert is_cancel_row("[취소공고] 한전본사 유지보수", None, None)               # 상태 모름 → 제목
    assert not is_cancel_row("(취소공고)(재공고) 포털 구축", None, None)          # 재공고는 산다
    assert not is_cancel_row("일반 공고", None, None)
    rows = [
        {"bid_ntce_no": "A", "bid_ntce_ord": "000", "bid_ntce_nm": "개보수공사", "status": "일반공고", "kind": None},
        {"bid_ntce_no": "A", "bid_ntce_ord": "001", "bid_ntce_nm": "개보수공사-취소공고", "status": "취소공고", "kind": None},
        {"bid_ntce_no": "B", "bid_ntce_ord": "000", "bid_ntce_nm": "재발주", "status": "일반공고", "kind": None},
        {"bid_ntce_no": "C", "bid_ntce_ord": "000", "bid_ntce_nm": "x", "status": None, "kind": None},
        {"bid_ntce_no": "C", "bid_ntce_ord": "001", "bid_ntce_nm": "x 취소 공고", "status": None, "kind": None},
        {"bid_ntce_no": "C", "bid_ntce_ord": "002", "bid_ntce_nm": "x 재입찰", "status": "재입찰공고", "kind": None},
    ]
    cmap = cancel_ords(rows)
    assert cmap == {"A": "001", "C": "001"}, cmap
    cands = [{"bid_ntce_no": n, "bid_ntce_ord": o} for n, o in [("A", "000"), ("A", "001"), ("B", "000"), ("C", "000"), ("C", "002")]]
    kept = [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in drop_cancelled(cands, cmap)]
    assert kept == [("B", "000"), ("C", "002")], kept     # 취소 차수 이하는 전부, 그 뒤 차수는 산다
    assert drop_cancelled(cands, {}) is cands
    print("ok")
