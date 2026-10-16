"""자격요건 하드 필터.

v1의 소프트 감점(-0.30)과 달리 미충족 공고는 후보에서 제외한다.
단, "회사 정보가 없어 검증 불가"는 탈락이 아니라 unverified로 통과시킨다 —
데이터 부재로 후보가 전멸하는 것을 막기 위함.
"""

from __future__ import annotations

# 행정구역 개편 전 이름이 양쪽(companies.rgn_nm, bid_rgn_limits)에 섞여 있다 — 비교 전에 현재 이름으로
_SIDO_ALIAS = {
    "전라남도": "전남광주통합특별시",
    "광주광역시": "전남광주통합특별시",
    "전라북도": "전북특별자치도",
    "강원도": "강원특별자치도",
}


def _rgn_tokens(s: str) -> list[str]:
    t = s.split()
    if t:
        t[0] = _SIDO_ALIAS.get(t[0], t[0])
    return t


def region_allows(allowed: str, company_rgn: str) -> bool:
    """제한 지역이 적은 단위까지만 비교한다 — '경상남도' 는 시·도, '경상남도 창원시' 는 시·군, '부산광역시 중구' 는 자치구.
    진행 중 지역 제한 공고의 42% 가 시·도보다 좁다(2026-10-16 실측). 옛 코드는 시·도만 비교해 김해 회사가 창원시 제한을 통과했다."""
    a, c = _rgn_tokens(allowed), _rgn_tokens(company_rgn)
    return bool(a) and c[: len(a)] == a


def check_qualifications(
    company_industry_names: set[str],
    company_rgn: str | None,
    licenses: list[dict],
    regions: list[dict],
) -> dict:
    """공고 1건의 면허/지역 제한 대비 회사 자격 판정.

    Return: {passed, unverified, reasons: [라벨...], failures: [라벨...]}
    """
    reasons: list[str] = []
    failures: list[str] = []
    unverified = False

    if not licenses:
        reasons.append("면허 제한 없음")
    elif not company_industry_names:
        unverified = True
        reasons.append("면허 확인불가")
    else:
        groups: dict[str, set[str]] = {}
        for lim in licenses:
            nm = (lim.get("lcns_lmt_nm") or "").strip()
            if not nm:
                continue
            name_only = nm.split("/")[0].strip()
            base = name_only.split("(")[0].strip()
            grp = str(lim.get("lmt_grp_no") or "1")
            groups.setdefault(grp, set()).update({name_only, base})

        failed_group = next(
            (
                needed
                for needed in groups.values()
                if needed and not (company_industry_names & needed)
            ),
            None,
        )
        if failed_group is None:
            reasons.append("면허 충족")
        else:
            sample = sorted(n for n in failed_group if n)[:2]
            failures.append(f"면허 미충족({', '.join(sample)})")

    if not regions:
        reasons.append("지역 제한 없음")
    elif not company_rgn:
        unverified = True
        reasons.append("지역 확인불가")
    else:
        allowed = [
            (lim.get("prtcpt_psbl_rgn_nm") or "").strip()
            for lim in regions
            if (lim.get("prtcpt_psbl_rgn_nm") or "").strip()
        ]
        if not allowed:
            reasons.append("지역 제한 없음")
        elif any(region_allows(a, company_rgn) for a in allowed):
            reasons.append("지역 자격 충족")
        else:
            failures.append(f"지역 미충족({allowed[0]}{' 외' if len(allowed) > 1 else ''})")

    return {
        "passed": not failures,
        "unverified": unverified,
        "reasons": reasons,
        "failures": failures,
    }


if __name__ == "__main__":   # uv run python -m app.recommender.qualifications
    assert region_allows("경상남도", "경상남도 김해시 삼정동")
    assert region_allows("경상남도 창원시", "경상남도 창원시 마산합포구")
    assert not region_allows("경상남도 창원시", "경상남도 김해시 삼정동")          # 옛 코드가 통과시키던 것
    assert region_allows("부산광역시 중구", "부산광역시 중구 중앙동") and not region_allows("부산광역시 중구", "부산광역시 동구 초량동")
    assert region_allows("전남광주통합특별시 목포시", "전라남도 목포시 산정동")     # 개편 전 이름
    assert region_allows("광주광역시", "전남광주통합특별시 동구") and not region_allows("", "경기도")
    r = check_qualifications({"x"}, "경상남도 김해시", [], [{"prtcpt_psbl_rgn_nm": "경상남도 창원시"}, {"prtcpt_psbl_rgn_nm": "경상남도 김해시"}])
    assert r["passed"] and r["reasons"] == ["면허 제한 없음", "지역 자격 충족"], r
    r = check_qualifications({"x"}, "경상남도 김해시", [], [{"prtcpt_psbl_rgn_nm": "경상남도 창원시"}])
    assert not r["passed"] and r["failures"] == ["지역 미충족(경상남도 창원시)"], r
    print("ok")
