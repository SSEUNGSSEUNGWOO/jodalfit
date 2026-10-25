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


# 회사 등록업종이 비어 면허를 판정할 수 없을 때("면허 확인불가")의 감점. 2026-10-25 실측: 벡터 있는 회사의 27%
# (20,976/78,727), 최근 30일 사용자가 검색한 회사의 10%(33/343)가 등록업종 0건이라 면허 제한 공고가 전부
# 확인불가로 통과했다(유원디자인연구소: 20건 중 15건 — 궤도회로 케이블 공사·건축공사까지). 값은 채점표로 정했다 —
# docs/recommender/exp-2026-10-25-unverified-cancelled.md. 지역 확인불가는 감점하지 않는다.
# 값 12 = 가장 센 보너스 하나(재출현 기관 +12)와 같은 크기 — 확인불가 공고가 제한 없음 공고를 앞서려면 보너스 하나 이상의
# 유사도 차이가 있어야 한다. 채점표 표본(낙찰 이력 회사)에는 업종 0건 회사가 2곳뿐이라 값은 측정이 아니라 판단이다.
UNVERIFIED_LICENSE_PENALTY = 12.0


def unverified_penalty(q: dict, penalty: float = UNVERIFIED_LICENSE_PENALTY) -> float:
    """check_qualifications 결과 q 에 대한 감점(양수). 회사 쪽 업종이 비어 판정 못 한 경우(license_unknown == "company")만.
    공고 쪽 면허 행이 없어 판정 못 한 경우("notice")는 라벨만 확인불가고 감점하지 않는다 — 2026-10-25 채점표: 8/1 시점 공고는
    면허 행 수집이 덜 돼 정답 공고까지 −12 를 먹고 final@20 이 −0.030(공사 −0.080) 떨어졌다. 그건 회사가 아니라 우리 자료의 구멍이다."""
    return penalty if q.get("license_unknown") == "company" else 0.0


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
    license_text: str | None = None,
) -> dict:
    """공고 1건의 면허/지역 제한 대비 회사 자격 판정.

    license_text: 공고의 허용업종 원문(bidprc_psbl_indstryty_nm). bid_license_limits 행이 없는데 원문이 있으면
    "제한 없음"이 아니라 "확인불가"다 — 2026-10-25 실측: 진행 공고 중 449건(제한 공고의 7%)이 이 상태였다.
    Return: {passed, unverified, reasons: [라벨...], failures: [라벨...]}
    """
    reasons: list[str] = []
    failures: list[str] = []
    unverified = False
    license_unknown: str | None = None   # "company"(회사 업종 미상) / "notice"(공고 면허 행 없음) — 감점은 company 만

    if not licenses:
        if (license_text or "").strip():
            unverified = True
            license_unknown = "notice"
            reasons.append("면허 확인불가")
        else:
            reasons.append("면허 제한 없음")
    elif not company_industry_names:
        unverified = True
        license_unknown = "company"
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

        # 제한 그룹(lmt_grp_no)은 서로 대안이다 — 어느 한 그룹의 면허 하나만 있으면 된다.
        # 2026-10-23 실측: 실제 입찰 참가자(자격이 있던 회사) 10,086쌍에서 그룹 AND 는 81.5%(그룹 2개+ 공고는 41.9%)만
        # 통과시켰고 그룹 OR 는 98.3%(98.9%). 그룹 안을 '전부 보유'로 보면 96.4% — 그룹 안도 하나면 된다.
        needed_all = [needed for needed in groups.values() if needed]
        if not needed_all or any(company_industry_names & needed for needed in needed_all):
            reasons.append("면허 충족")
        else:
            sample = sorted({n for needed in needed_all for n in needed if n})[:2]
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
        "license_unknown": license_unknown,
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
    lic = [{"lcns_lmt_nm": "안전진단전문기관(건축분야)/1", "lmt_grp_no": "1"},
           {"lcns_lmt_nm": "안전점검전문기관(건축 분야)/2", "lmt_grp_no": "2"}]
    assert check_qualifications({"안전점검전문기관(건축 분야)"}, None, lic, [])["passed"]   # 그룹은 대안(OR)
    r = check_qualifications({"건축공사업"}, None, lic, [])
    assert not r["passed"] and r["failures"] == ["면허 미충족(안전점검전문기관, 안전점검전문기관(건축 분야))"], r
    lic = [{"lcns_lmt_nm": "일반소방시설공사업(기계)", "lmt_grp_no": "1"}, {"lcns_lmt_nm": "일반소방시설공사업(전기)", "lmt_grp_no": "1"}]
    assert check_qualifications({"일반소방시설공사업(전기)"}, None, lic, [])["passed"]       # 그룹 안도 하나면 된다
    r = check_qualifications(set(), None, lic, [])
    assert r["passed"] and r["unverified"] and unverified_penalty(r, 9.0) == 9.0           # 업종 미상 → 확인불가 통과 + 감점
    assert unverified_penalty(check_qualifications(set(), None, [], []), 9.0) == 0.0        # 면허 제한 없음 → 감점 없음
    r = check_qualifications({"x"}, None, [], [], license_text="산업디자인전문회사(환경디자인분야)")
    assert r["passed"] and r["unverified"] and r["reasons"][0] == "면허 확인불가", r          # 행 없음 + 원문 있음 → 확인불가
    assert r["license_unknown"] == "notice" and unverified_penalty(r, 9.0) == 0.0                # 공고 쪽 구멍은 감점하지 않는다
    assert check_qualifications({"x"}, None, [], [], license_text="  ")["reasons"][0] == "면허 제한 없음"
    print("ok")
