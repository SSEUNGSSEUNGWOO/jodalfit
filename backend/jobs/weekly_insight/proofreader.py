"""Proofreader 에이전트 — Claude Code CLI.

마크다운 본문에 대해 오타/문장부호/한자 정리만. 내용 변경 X.
"""

from __future__ import annotations

import os
import shutil
import subprocess


PROOFREAD_TIMEOUT = 180


PROMPT_TEMPLATE = """다음은 공공조달 주간 인사이트 마크다운입니다. 아래 항목만 수정하고 수정된 전체 텍스트를 그대로 반환하세요.

수정 항목:
- 오타 교정
- 마침표/쉼표/따옴표 등 문장부호 오류
- 어색한 띄어쓰기
- 한자(漢字)가 의미 없이 삽입된 경우 자연스러운 한국어로 교체
- 마크다운 구조 오류 (헤더 깨짐, 표 정렬 불일치)

절대 하지 말 것:
- 내용 변경, 요약, 재작성
- 표 안의 숫자 수정
- 링크 URL 수정
- 문장 추가/삭제
- 수정 내역 설명 출력. 오직 수정된 전체 마크다운 본문만 출력.

원본은 ---로 시작하는 frontmatter가 있을 수 있다. frontmatter는 손대지 말고 그대로 출력.

---

{draft}
"""


def proofread(draft: str) -> str:
    prompt = PROMPT_TEMPLATE.format(draft=draft)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    claude_cmd = shutil.which("claude") or "claude"
    try:
        result = subprocess.run(
            [claude_cmd, "-p", "-"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=PROOFREAD_TIMEOUT,
            env=env,
            encoding="utf-8",
            shell=True,
        )
    except subprocess.TimeoutExpired:
        print("[proofreader] timeout — 원본 유지")
        return draft

    if result.returncode != 0:
        print(f"[proofreader] CLI 실패, 원본 유지: {result.stderr[:200]}")
        return draft

    out = result.stdout.strip().strip("`")
    if not out:
        return draft

    # 코드펜스 prefix 제거
    if out.startswith("markdown\n"):
        out = out[len("markdown\n") :]

    # frontmatter가 있는 원본은 그대로 시작해야. 없으면 첫 '#'부터 자르기.
    if draft.lstrip().startswith("---"):
        idx = out.find("---")
        if idx >= 0:
            out = out[idx:]
    else:
        idx = out.find("#")
        if idx >= 0:
            out = out[idx:]

    print("[proofreader] 교정 완료")
    return out
