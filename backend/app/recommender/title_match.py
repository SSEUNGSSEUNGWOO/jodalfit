"""키워드 모드의 글자 일치 — "제목·발주기관·참가 지역에 그 말이 든 진행 공고 전부".

키워드 검색은 질의를 임베딩해 뜻이 가까운 순으로 20건을 자르는데, 그 방식에는 "해당하는 공고" 의 경계가
없다(모든 공고가 조금씩은 비슷하다). 2026-10-27 실측: 제목에 "옥상방수" 가 든 진행 공고는 14건인데 20건을
내니 뜻만 비슷한 것이 섞였고, "폐기물" 은 378건인데 20건만 보여 358건을 놓쳤다. 키워드로 검색하는 사람은
추천이 아니라 찾기를 하므로, 글자 일치 전부를 먼저 주고 의미 유사 20건은 그 밖의 것으로 뒤에 둔다.

2026-10-28: 30일 키워드 질의 590건의 80% 가 한 낱말이고 그 상당수가 지역·기관명이었다(여수·평택·옥천·국무조정실…).
제목만 보면 "옥천" 13건·"여수" 9건인데 발주기관·참가 가능 지역까지 보면 28건·172건, 기관명 질의는 제목 0건이라
의미 유사 20건만 떴다. 그래서 낱말마다 제목·수요기관·공고기관·참가 가능 지역 네 열 OR(낱말끼리는 AND)로 찾는다.

이 모듈은 순수 로직만 — 질의를 낱말로 쪼개 PostgREST 필터를 만들고, 받은 행을 차수·취소·상한으로 정리한다.
DB 호출은 app/services/recommend.py::_search_title_matches. 회사 모드 점수에는 손대지 않는다.
자체 점검: `uv run python -m app.recommender.title_match`
"""

from __future__ import annotations

import re

from app.recommender.cancellation import drop_cancelled

MAX_TERMS = 5     # 낱말은 다섯 개까지 — 그 이상은 AND 가 비어 어차피 0건
MIN_TERM_LEN = 2  # 한 글자("문")는 너무 넓다
CAP = 300         # 응답에 싣는 상한. "공사" 같은 낱말은 2,300건이라 마감 가까운 순으로 자른다

_SPLIT = re.compile(r"[\s,/·|]+")
_ASCII = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")
_STRIP = "\"'()[]{}<>*"


def parse_terms(text: str) -> list[str]:
    """질의 → 낱말 목록(중복 제거, 소문자 비교, 최대 MAX_TERMS). 약어 풀이는 적용하지 않는다 — 글자 그대로 찾는다."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in _SPLIT.split(text or ""):
        t = raw.strip(_STRIP)
        if len(t) < MIN_TERM_LEN or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t)
        if len(out) >= MAX_TERMS:
            break
    return out


# 낱말을 찾는 열 — 제목, 수요기관, 공고기관, 참가 가능 지역("전남광주통합특별시 여수시,…" 같은 목록이라 부분 일치가 맞다)
MATCH_COLS = ("bid_ntce_nm", "dmnd_instt_nm", "ntce_instt_nm", "prtcpt_psbl_rgn_nm")
DIVISIONS = ("물품", "용역", "공사")   # bsns_div_nm 값. 외자(45건)는 칩을 두지 않는다


def _quote(v: str) -> str:
    """PostgREST or=(…) 안의 값 — 쉼표·점·괄호가 들어가면 큰따옴표로 싸야 하고, 그 안에서는 \\ 가 이스케이프다."""
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def term_filters(terms: list[str]) -> list[tuple[str, str]]:
    """낱말마다 PostgREST (연산자, 조건). 전부 AND.

    영문·숫자 낱말은 단어 경계 정규식 — "si" 를 부분 일치로 찾으면 design·Lattice 가 잡힌다(진행 공고 34건 중
    실제 SI 는 1건, 2026-10-27). 한글은 부분 일치 — "옥상방수" 는 "옥상방수공사" 안에 있다.
    """
    out: list[tuple[str, str]] = []
    for t in terms:
        if _ASCII.fullmatch(t):
            out.append(("imatch", f"(^|[^a-z0-9]){re.escape(t)}([^a-z0-9]|$)"))
        else:
            like = t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            out.append(("ilike", f"*{like}*"))   # PostgREST 는 * 를 % 로 읽는다
    return out


def term_or_filters(terms: list[str]) -> list[str]:
    """낱말마다 `or=(…)` 한 개 — MATCH_COLS 네 열 중 하나라도 맞으면. 낱말끼리는 or 파라미터를 거듭 붙여 AND."""
    return [",".join(f"{c}.{op}.{_quote(crit)}" for c in MATCH_COLS) for op, crit in term_filters(terms)]


def matched_in(row: dict, terms: list[str]) -> list[str]:
    """제목에 없는 낱말이 어디서 맞았는가 — ("기관" | "지역") 목록, 제목에 다 있으면 빈 목록. 화면의 칩 근거."""
    title = (row.get("bid_ntce_nm") or "").lower()
    instt = ((row.get("dmnd_instt_nm") or "") + " " + (row.get("ntce_instt_nm") or "")).lower()
    rgn = (row.get("prtcpt_psbl_rgn_nm") or "").lower()
    out: list[str] = []
    for t in terms:
        k = t.lower()
        if k in title:
            continue
        where = "기관" if k in instt else "지역" if k in rgn else None
        if where and where not in out:
            out.append(where)
    return out


def select_rows(rows: list[dict], cmap: dict[str, str], cap: int = CAP) -> tuple[list[dict], bool]:
    """같은 공고번호는 가장 큰 차수 하나만, 취소공고(와 그 원공고)는 빼고, 마감 가까운 순으로 cap 까지.
    반환: (행, 잘렸는가)."""
    latest: dict[str, dict] = {}
    for r in rows:
        no = r.get("bid_ntce_no") or ""
        if not no:
            continue
        cur = latest.get(no)
        if cur is None or (r.get("bid_ntce_ord") or "000") > (cur.get("bid_ntce_ord") or "000"):
            latest[no] = r
    kept = drop_cancelled(list(latest.values()), cmap)
    kept.sort(key=lambda r: ((r.get("bid_clse_date") or "9999-12-31"), r.get("bid_ntce_no") or ""))
    return kept[:cap], len(kept) > cap


if __name__ == "__main__":   # uv run python -m app.recommender.title_match
    assert parse_terms("옥상방수") == ["옥상방수"]
    assert parse_terms(" 옥상 방수, 공사/설계 ") == ["옥상", "방수", "공사", "설계"]
    assert parse_terms("SI si Si") == ["SI"]                       # 대소문자 중복 한 번만
    assert parse_terms("문 a 폐기물") == ["폐기물"]                 # 한 글자는 버린다
    assert parse_terms("a1 b2 c3 d4 e5 f6 g7") == ["a1", "b2", "c3", "d4", "e5"]
    assert parse_terms("(cctv) '설치'") == ["cctv", "설치"]
    assert parse_terms("") == []

    f = term_filters(["si", "옥상방수", "100%", "c-2"])
    assert f[0] == ("imatch", "(^|[^a-z0-9])si([^a-z0-9]|$)"), f[0]
    assert f[1] == ("ilike", "*옥상방수*"), f[1]
    assert f[2] == ("ilike", "*100\\%*"), f[2]                  # LIKE 특수문자는 이스케이프
    assert f[3] == ("imatch", "(^|[^a-z0-9])c\\-2([^a-z0-9]|$)"), f[3]

    o = term_or_filters(["옥천", "100%"])
    assert len(o) == 2 and o[0] == ",".join(f'{c}.ilike."*옥천*"' for c in MATCH_COLS), o[0]
    assert o[1].startswith('bid_ntce_nm.ilike."*100\\\\%*"'), o[1]    # 따옴표 안에서 \ 는 한 번 더
    assert matched_in({"bid_ntce_nm": "옥천읍 도로", "dmnd_instt_nm": "옥천군"}, ["옥천"]) == []
    assert matched_in({"bid_ntce_nm": "도로 보수", "dmnd_instt_nm": "옥천군"}, ["옥천"]) == ["기관"]
    assert matched_in({"bid_ntce_nm": "도로 보수", "prtcpt_psbl_rgn_nm": "충청북도 옥천군"}, ["옥천", "도로"]) == ["지역"]
    assert matched_in({"bid_ntce_nm": "도로", "ntce_instt_nm": "옥천군", "prtcpt_psbl_rgn_nm": "여수시"}, ["옥천", "여수"]) == ["기관", "지역"]

    rows = [
        {"bid_ntce_no": "A", "bid_ntce_ord": "000", "bid_clse_date": "2026-11-03"},
        {"bid_ntce_no": "A", "bid_ntce_ord": "001", "bid_clse_date": "2026-11-05"},   # 정정 차수 — 이것만 남는다
        {"bid_ntce_no": "B", "bid_ntce_ord": "000", "bid_clse_date": "2026-11-01"},
        {"bid_ntce_no": "C", "bid_ntce_ord": "000", "bid_clse_date": "2026-11-02"},   # 취소된 원공고
        {"bid_ntce_no": "D", "bid_ntce_ord": "000", "bid_clse_date": None},
    ]
    kept, capped = select_rows(rows, {"C": "000"})
    assert [(r["bid_ntce_no"], r["bid_ntce_ord"]) for r in kept] == [("B", "000"), ("A", "001"), ("D", "000")], kept
    assert capped is False
    kept, capped = select_rows(rows, {}, cap=2)
    assert len(kept) == 2 and capped is True
    print("title_match: ok")
