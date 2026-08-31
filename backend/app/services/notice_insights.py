"""첨부문서 텍스트 → 구조화 인사이트 (gpt-4o-mini, JSON schema).

입력은 bid_notice_documents의 추출 텍스트. 제안요청서·과업지시서 계열을 앞에 두고
MAX_INPUT_CHARS까지만 잘라 보낸다 (비용 통제: 공고당 ≈ 8k 토큰).
"""

from __future__ import annotations

import json
import re

from app.services.openai_client import get_openai_client

MODEL = "gpt-4o-mini"
MAX_INPUT_CHARS = 12_000

_PRIORITY = [
    (re.compile(r"제안\s*요청|과업\s*(지시|내용|설명)|규격서|사양서|RFP", re.I), 0),
    (re.compile(r"공고"), 1),
]


def _priority(name: str | None) -> int:
    for pat, p in _PRIORITY:
        if name and pat.search(name):
            return p
    return 2


def build_input(docs: list[dict]) -> tuple[str, list[int]]:
    """문서들을 우선순위 순으로 이어붙여 입력 텍스트 생성. (text, 사용한 seq 목록)"""
    docs = sorted(docs, key=lambda d: (_priority(d.get("file_name")), d.get("seq", 0)))
    parts: list[str] = []
    seqs: list[int] = []
    remaining = MAX_INPUT_CHARS
    for d in docs:
        text = (d.get("text") or "").strip()
        if not text or remaining < 500:
            continue
        chunk = text[:remaining]
        parts.append(f"===== 파일: {d.get('file_name') or d.get('seq')} =====\n{chunk}")
        seqs.append(d["seq"])
        remaining -= len(chunk)
    return "\n\n".join(parts), seqs


SYSTEM = """당신은 한국 공공조달(나라장터) 입찰 문서 분석가입니다.
제안요청서·과업지시서·입찰공고문 텍스트를 읽고, 입찰 참여를 검토하는 중소기업 실무자에게 필요한 정보만 구조화합니다.

규칙:
- 문서에 명시된 내용만 쓴다. 추측·일반론 금지. 없으면 null 또는 빈 배열.
- summary: 무엇을 만들거나 수행하는 사업인지 2~3문장, 총 120~200자. 발주기관명·사업명 반복 금지, 과업 핵심 위주.
- scope: 주요 과업 항목 3~6개, 각 30자 이내 명사구.
- requirements: 참가자격·필수 조건. 법 조문 인용은 빼고 실무자가 확인해야 할 조건만 (예: "소프트웨어사업자 신고", "직접생산확인증명서(정보시스템개발서비스)", "최근 3년 유사실적 5억 이상", "중소기업 확인서", "본사 소재지 대구"). kind는 license(면허·업종등록), certification(인증·확인서), performance(실적), region(지역), company_size(기업규모), other 중 하나. mandatory는 필수 여부.
- evaluation: 낙찰자 결정 방식(method), 기술/가격 배점 비율(technical_pct/price_pct, 숫자만), 제안 발표(PT) 유무(presentation), 기타 특이사항(note, 40자 이내).
- keywords: 매칭에 쓸 기술·도메인 용어 4~8개 (예: "그룹웨어", "전자결재", "PostgreSQL", "GIS", "CCTV"). 일반어("사업", "용역", "시스템") 단독 금지.
- 모두 한국어. 원문 표기(영문 약어 등)는 그대로."""

SCHEMA = {
    "name": "bid_notice_insight",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "scope": {"type": "array", "items": {"type": "string"}},
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": ["license", "certification", "performance", "region", "company_size", "other"],
                        },
                        "text": {"type": "string"},
                        "mandatory": {"type": "boolean"},
                    },
                    "required": ["kind", "text", "mandatory"],
                },
            },
            "evaluation": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "method": {"type": ["string", "null"]},
                    "technical_pct": {"type": ["number", "null"]},
                    "price_pct": {"type": ["number", "null"]},
                    "presentation": {"type": ["boolean", "null"]},
                    "note": {"type": ["string", "null"]},
                },
                "required": ["method", "technical_pct", "price_pct", "presentation", "note"],
            },
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "scope", "requirements", "evaluation", "keywords"],
    },
}


def summarize(notice_name: str, input_text: str) -> dict:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"[공고명] {notice_name}\n\n{input_text}"},
        ],
        temperature=0.1,
        max_tokens=900,
        response_format={"type": "json_schema", "json_schema": SCHEMA},
    )
    return json.loads(resp.choices[0].message.content)
