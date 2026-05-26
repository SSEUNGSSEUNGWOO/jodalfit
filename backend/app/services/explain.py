"""추천 이유 LLM 설명 (차별화 핵심).

회사 컨텍스트 + 추천 공고 → "왜 추천했는지" 자연어 설명.
모델: gpt-4o-mini (저렴 + 충분).
"""

from __future__ import annotations

from app.services.openai_client import get_openai_client

MODEL = "gpt-4o-mini"


SYSTEM_COMPANY = """당신은 한국 공공조달(나라장터) 입찰공고 추천 설명 모듈입니다.

# 작성 규칙
- **반드시 매칭 시그널 중 가장 강한 한 가지를 골라 그 구체 데이터를 인용**해 설명
  (예: 같은 기관 거래 이력, 등록업종 토큰 일치, 평균 수주가 ratio, 지역 일치)
- 한 줄로 70~110자, 단정형 어미("…한 매칭이다", "…와 정확히 겹친다")
- 일반론 금지: "업무가 맞다", "강점이 있다", "관련 있는 분야" 같은 추상 표현 ❌
- 회사 이름·기관명·등록업종 같은 **고유명사를 한 번 이상 인용**
- "귀사", "이 회사는" 같은 헤지 호칭 X — 사실 1줄로 바로 시작
- 매번 다른 시그널을 강조해 5건 설명이 서로 다르게 보이도록

# 좋은 예
- "과거 한국에너지공단과 거래 이력이 있어 같은 기관의 후속 사업과 정확히 겹친다."
- "회사 평균 수주가 7억대인데 이 공고도 6.5억 규모로 사업 체급이 맞물린다."
- "회사 등록업종 '소프트웨어사업자'와 공고 참가가능업종이 토큰 3개 일치한다."
- "공고 발주처가 경기도여서 회사 지역 가산이 적용된 매칭이다."

# 나쁜 예 (절대 금지)
- "이 공고는 귀사의 업무와 잘 맞아 추천드립니다."
- "과거 수주 이력과 유사한 분야의 공고입니다."
- "회사의 강점이 발휘될 수 있는 사업입니다."
"""


SYSTEM_KEYWORDS = """당신은 한국 공공조달(나라장터) 입찰공고 추천 설명 모듈입니다.

키워드 모드 — 사용자가 입력한 키워드와 공고 사이의 의미적 연결고리를 설명합니다.

# 작성 규칙
- 회사·귀사·이 회사 같은 호칭 절대 금지
- **공고의 도메인·기관·작업 성격 중 키워드와 가장 가까운 부분을 구체 인용**
- 한 줄로 70~100자, 단정형
- 키워드 단어를 그대로 반복하지 말고, 의미적 연결을 풀어서 짚을 것
- 일반론 금지: "관련된 공고", "비슷한 분야"  ❌

# 좋은 예
- "검색어 '교육 IT 유지보수'와 같은 도메인의 충북교육청 학습 시스템 운영 사업이다."
- "도로 정비 키워드와 직접 일치하지는 않지만 한국도로공사의 포장 유지보수와 작업 성격이 같다."
"""


def _format_amount(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v / 10_000:.0f}만"
    return f"{int(v):,}"


def _strongest_signal(detail: dict) -> str | None:
    """bonus_detail 중 가장 강한 회사↔공고 매칭 시그널을 한국어로 표현.

    dday_sweet 같은 운영 편의 시그널(검토 시간 여유 등)은 매칭 이유가 아니므로
    제외 — dict 형태로 들어온 매칭 시그널만 후보로 인정.
    """
    if not detail:
        return None
    candidates: list[tuple[float, str]] = []
    for k, v in detail.items():
        if not isinstance(v, dict):
            continue
        score = v.get("score", 0)
        if k == "institution_familiar":
            candidates.append((score, f"과거 거래 기관 '{v.get('instt')}'과 정확히 일치"))
        elif k == "industry_tokens":
            matched = v.get("matched") or []
            if matched:
                candidates.append(
                    (score, f"회사 등록업종/공급물품의 토큰 {len(matched)}개 일치: {', '.join(matched[:3])}")
                )
        elif k == "amount_fit":
            ratio = v.get("ratio")
            cm = _format_amount(v.get("company_median"))
            np = _format_amount(v.get("notice_price"))
            candidates.append(
                (score, f"회사 평균 수주가 {cm} vs 공고 {np} (ratio {ratio}) — 체급 적합")
            )
        elif k == "region_match":
            candidates.append((score, f"회사 지역과 공고 참가가능지역 '{v.get('rgn')}'이 일치"))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def build_company_prompt(company: dict, bid: dict) -> str:
    lines = []
    lines.append(f"[회사] {company.get('corp_nm') or '—'}")
    extras: list[str] = []
    if company.get("corp_bsns_div_nm"):
        extras.append(f"업무 {company['corp_bsns_div_nm']}")
    if company.get("rgn_nm"):
        extras.append(f"지역 {company['rgn_nm']}")
    if extras:
        lines.append("       " + " · ".join(extras))

    lines.append(f"\n[공고] {bid.get('bid_ntce_nm') or '—'}")
    bid_meta: list[str] = []
    if bid.get("bsns_div_nm"):
        bid_meta.append(bid["bsns_div_nm"])
    if bid.get("dmnd_instt_nm"):
        bid_meta.append(f"발주 {bid['dmnd_instt_nm']}")
    if bid.get("presmpt_prce"):
        bid_meta.append(f"추정 {_format_amount(bid['presmpt_prce'])}")
    if bid.get("bidprc_psbl_indstryty_nm"):
        bid_meta.append(f"참가가능업종 {bid['bidprc_psbl_indstryty_nm']}")
    if bid_meta:
        lines.append("       " + " · ".join(bid_meta))

    strongest = _strongest_signal(bid.get("bonus_detail") or {})
    if strongest:
        lines.append(f"\n[강한 시그널] {strongest}")
        lines.append("→ 위 시그널을 본문에 구체적으로 인용해 한 줄로 설명할 것")
    else:
        lines.append(
            "\n[강한 시그널] 없음 (코사인 유사도만 기반) — 회사 업무 영역과 공고 텍스트의 의미적 연결을 짚을 것"
        )

    lines.append(
        f"\n[점수] base={bid.get('base_similarity', 0):.3f} + bonus={bid.get('bonus', 0):+.3f}"
    )
    return "\n".join(lines)


def build_keyword_prompt(query: str, bid: dict) -> str:
    lines = []
    lines.append(f'[검색 키워드] "{query}"')
    lines.append(f"\n[공고] {bid.get('bid_ntce_nm') or '—'}")
    bid_meta: list[str] = []
    if bid.get("bsns_div_nm"):
        bid_meta.append(bid["bsns_div_nm"])
    if bid.get("dmnd_instt_nm"):
        bid_meta.append(f"발주 {bid['dmnd_instt_nm']}")
    if bid.get("presmpt_prce"):
        bid_meta.append(f"추정 {_format_amount(bid['presmpt_prce'])}")
    if bid.get("bidprc_psbl_indstryty_nm"):
        bid_meta.append(f"참가가능업종 {bid['bidprc_psbl_indstryty_nm']}")
    if bid_meta:
        lines.append("       " + " · ".join(bid_meta))
    lines.append(
        f"\n[의미 유사도] {bid.get('base_similarity', 0):.3f} (1.0 = 완전 일치)"
    )
    lines.append(
        "→ 키워드와 공고 사이의 가장 강한 의미적 연결(도메인/기관 유형/작업 성격) 한 가지를 골라 70~100자로 단정형 설명."
    )
    return "\n".join(lines)


def explain_recommendation(company: dict, bid: dict) -> str:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_COMPANY},
            {"role": "user", "content": build_company_prompt(company, bid)},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


def explain_keyword_match(query: str, bid: dict) -> str:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_KEYWORDS},
            {"role": "user", "content": build_keyword_prompt(query, bid)},
        ],
        temperature=0.3,
        max_tokens=180,
    )
    return resp.choices[0].message.content.strip()


def explain_batch(
    company: dict, bids: list[dict], max_workers: int = 5
) -> list[str]:
    """회사 모드 병렬 LLM 설명."""
    from concurrent.futures import ThreadPoolExecutor

    if not bids:
        return []
    results: list[str] = [""] * len(bids)
    with ThreadPoolExecutor(max_workers=min(max_workers, len(bids))) as ex:
        future_to_idx = {
            ex.submit(explain_recommendation, company, b): i for i, b in enumerate(bids)
        }
        for fut in future_to_idx:
            idx = future_to_idx[fut]
            try:
                results[idx] = fut.result(timeout=30)
            except Exception as e:
                results[idx] = f"(설명 생성 실패: {type(e).__name__})"
    return results


def explain_keyword_batch(
    query: str, bids: list[dict], max_workers: int = 5
) -> list[str]:
    """키워드 모드 병렬 LLM 설명 — '귀사' 같은 회사 호칭 안 씀."""
    from concurrent.futures import ThreadPoolExecutor

    if not bids:
        return []
    results: list[str] = [""] * len(bids)
    with ThreadPoolExecutor(max_workers=min(max_workers, len(bids))) as ex:
        future_to_idx = {
            ex.submit(explain_keyword_match, query, b): i for i, b in enumerate(bids)
        }
        for fut in future_to_idx:
            idx = future_to_idx[fut]
            try:
                results[idx] = fut.result(timeout=30)
            except Exception as e:
                results[idx] = f"(설명 생성 실패: {type(e).__name__})"
    return results
