"""추천 이유 LLM 설명 (차별화 핵심).

회사 컨텍스트 + 추천 공고 → "왜 추천했는지" 자연어 설명.
모델: gpt-4o-mini (저렴 + 충분).
"""

from __future__ import annotations

from app.services.openai_client import get_openai_client

MODEL = "gpt-4o-mini"


SYSTEM = """당신은 한국 공공조달(나라장터) 입찰공고 추천 서비스의 설명 모듈입니다.
주어진 회사 정보와 추천된 공고에 대해 '왜 이 공고가 이 회사에 맞는지' 2~3줄로 간결하게 설명하세요.
- 추측 금지, 주어진 데이터만 사용
- 친근한 톤
- 한국어로
- '~할 가능성', '~로 보입니다' 등 과한 헤지 표현 피하기"""


def build_user_prompt(company: dict, bid: dict) -> str:
    lines = []
    lines.append("[회사 정보]")
    lines.append(f"- 이름: {company.get('corp_nm')}")
    if company.get("corp_bsns_div_nm"):
        lines.append(f"- 업무구분: {company['corp_bsns_div_nm']}")
    if company.get("rgn_nm"):
        lines.append(f"- 지역: {company['rgn_nm']}")

    lines.append("\n[추천 공고]")
    lines.append(f"- 공고명: {bid.get('bid_ntce_nm')}")
    if bid.get("bsns_div_nm"):
        lines.append(f"- 업무구분: {bid['bsns_div_nm']}")
    if bid.get("bidprc_psbl_indstryty_nm"):
        lines.append(f"- 참가가능업종: {bid['bidprc_psbl_indstryty_nm']}")
    if bid.get("dmnd_instt_nm"):
        lines.append(f"- 수요기관: {bid['dmnd_instt_nm']}")
    if bid.get("presmpt_prce"):
        lines.append(f"- 추정가격: {bid['presmpt_prce']:,}원")
    if bid.get("bid_clse_date"):
        lines.append(f"- 입찰마감일: {bid['bid_clse_date']}")

    lines.append(f"\n[매칭 점수] similarity={bid.get('base_similarity', 0):.3f} bonus={bid.get('bonus', 0):+.3f}")

    return "\n".join(lines)


def explain_recommendation(company: dict, bid: dict) -> str:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_user_prompt(company, bid)},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


def explain_batch(company: dict, bids: list[dict]) -> list[str]:
    """배치 호출 (병렬 X, 일단 직렬). 추후 asyncio로 병렬화 가능."""
    return [explain_recommendation(company, b) for b in bids]
