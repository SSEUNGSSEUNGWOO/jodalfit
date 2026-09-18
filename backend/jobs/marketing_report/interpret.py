"""해석기 — Claude CLI(구독, `claude -p`) 가 비교표 마크다운만 읽고 300자 안팎 해석을 쓴다. 숫자는 만들지 않는다."""

from __future__ import annotations

import shutil
import subprocess

TIMEOUT = 120

PROMPT = """아래는 조달핏(나라장터 입찰공고 추천 서비스, jodalfit.co.kr)의 일일 마케팅 성적표 표다.
표만 근거로 한국어 250~350자, 한 단락으로 써라. 구성: (1) 오늘 눈에 띄는 것 1~2개 (2) 왜 그런지 표에서 읽히는 원인 (3) 오늘 할 일 1개.

규칙:
- 표에 없는 숫자·사실을 만들지 않는다. 표에 "—"나 "미수집"이면 그 항목은 판단하지 않는다.
- "활발한", "긍정적인" 같은 일반론 금지. 수치와 항목명을 그대로 인용한다.
- 구글은 색인 자체가 안 된 상태(발견됨-미색인 6만 건)라 구글 노출 0은 예상된 결과다. 색인 표본 비율이 오르는지가 관건.
- 성공 기준은 신규 유입이 아니라 재검색율(사람이 같은 회사를 7일 안에 다시 검색)이다.
- 출력은 해석 단락만. 제목·머리말·마크다운 없이.

{table}
"""


def interpret(table_md: str) -> str:
    claude = shutil.which("claude") or "claude"
    res = subprocess.run(
        [claude, "-p", "-"],
        input=PROMPT.format(table=table_md),
        capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT,
    )
    if res.returncode != 0:
        raise RuntimeError(f"claude CLI 실패: {res.stderr[:300]}")
    return res.stdout.strip()
