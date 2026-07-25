"""자격요건 하드 필터.

v1의 소프트 감점(-0.30)과 달리 미충족 공고는 후보에서 제외한다.
단, "회사 정보가 없어 검증 불가"는 탈락이 아니라 unverified로 통과시킨다 —
데이터 부재로 후보가 전멸하는 것을 막기 위함.
"""

from __future__ import annotations


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
        company_sido = company_rgn.split()[0]
        allowed = [
            (lim.get("prtcpt_psbl_rgn_nm") or "").strip()
            for lim in regions
            if (lim.get("prtcpt_psbl_rgn_nm") or "").strip()
        ]
        if not allowed:
            reasons.append("지역 제한 없음")
        elif any(a.split()[0] == company_sido or company_sido in a for a in allowed):
            reasons.append("지역 자격 충족")
        else:
            failures.append(f"지역 미충족({allowed[0]}{' 외' if len(allowed) > 1 else ''})")

    return {
        "passed": not failures,
        "unverified": unverified,
        "reasons": reasons,
        "failures": failures,
    }
