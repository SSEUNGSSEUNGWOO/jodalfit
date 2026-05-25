"""Writer 에이전트 — Claude Code CLI 서브프로세스.

ANTHROPIC_API_KEY 제거 → Anthropic Max 구독으로 호출.
공고 정보 → 12~25자 blurb 10개 (한 번 호출).
시장 통계 → 3~5문장 narrative 1개.
재시도 시 evaluator 피드백 받아 톤/구체성 보정.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

from .selectors import format_amount


CLAUDE_TIMEOUT = 180


def _claude_call(prompt: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    claude_cmd = shutil.which("claude") or "claude"
    result = subprocess.run(
        [claude_cmd, "-p", "-"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT,
        env=env,
        encoding="utf-8",
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI 실패: {result.stderr[:300]}")
    return result.stdout.strip()


def _extract_json(s: str):
    s = s.strip()
    # 코드펜스 제거
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
        for prefix in ("json", "JSON"):
            if s.startswith(prefix):
                s = s[len(prefix):].lstrip()
    candidates = [c for c in (s.find("{"), s.find("[")) if c >= 0]
    if not candidates:
        raise ValueError(f"JSON 시작 토큰 없음: {s[:200]}")
    start = min(candidates)
    end_char = "]" if s[start] == "[" else "}"
    end = s.rfind(end_char) + 1
    if end <= start:
        raise ValueError(f"JSON 종료 토큰 없음: {s[:200]}")
    return json.loads(s[start:end])


def write_picks_blurbs(picks: list[dict], feedback: str | None = None) -> list[str]:
    """공고 10건 → 12~25자 blurb 10개 (JSON 한 번 호출)."""
    items_json = json.dumps(
        [
            {
                "i": i + 1,
                "nm": p.get("bid_ntce_nm"),
                "bsns": p.get("bsns_div_nm"),
                "instt": p.get("dmnd_instt_nm") or p.get("ntce_instt_nm"),
                "price": format_amount(p.get("_price")),
                "dday": f"D-{p['_dday']}" if p["_dday"] else "D-Day",
            }
            for i, p in enumerate(picks)
        ],
        ensure_ascii=False,
    )

    feedback_block = (
        f"\n\n## 직전 평가자 피드백 (반영 필수)\n{feedback}\n"
        if feedback
        else ""
    )

    prompt = f"""당신은 한국 공공조달 큐레이션 에디터입니다. 공고 10건에 각각 12~25자 한국어 한 줄 blurb을 답니다.

규칙:
- 사실 기반, 추측 금지, 헤지 표현 금지 ("~할 가능성", "~로 보입니다")
- 공허한 일반론 금지 ("활발한", "주목할 만한", "다양한")
- 제목을 그대로 줄이지 말고, 규모/마감 텍스처/도메인 힌트 중 1개를 골라 한 줄
- 톤: jodalfit은 "검토할 만한" 디스커버리. "따낼 만한" 금지.
- 좋은 예: "교육기관 IT 유지보수, 마감 여유 11일"
           "150억 빗물펌프장 공사, 마감 임박 3일"
- 나쁜 예: "주목할 만한 공고, 검토 필요"
           "공공기관의 활발한 발주"

응답: JSON 배열만 출력. 다른 텍스트 금지.
형식: [{{"i":1,"blurb":"..."}}, {{"i":2,"blurb":"..."}}, ...]
{feedback_block}

## 공고 목록
{items_json}
"""
    raw = _claude_call(prompt)
    parsed = _extract_json(raw)
    by_i = {item["i"]: item["blurb"].strip().strip("\"'") for item in parsed}
    return [by_i.get(i + 1, "") for i in range(len(picks))]


def write_image_prompt(content_type: str, context: str) -> str:
    """주간 인사이트 커버 이미지용 한국어 프롬프트 생성.

    사용자가 이 프롬프트를 외부 도구(클로드 디자인/DALL-E/Imagen 등)에 그대로 넣어
    이미지를 만들고 frontmatter `cover_image:` 경로에 직접 등록.
    """
    style_brief = (
        "jodalfit 비주얼 가이드: 토스 톤(깨끗한 흰색 배경, 미니멀, 큰 여백), "
        "주조색은 딥 포레스트 그린(#166534), "
        "삽화는 평면적·기하학적·차분함, 사람 얼굴/캐릭터 금지, "
        "한글 텍스트 금지(이미지에 글자 X), 사진보다 일러스트레이션, "
        "1200x630 가로 와이드, 좌측에 비주얼·우측 여백(텍스트 오버레이용)."
    )
    type_brief = (
        "공공조달 큐레이션(서류·체크박스·승인 인장·돋보기·공공기관 건물·계약 등의 상징)"
        if content_type == "picks"
        else "데이터 리포트(막대그래프·도넛차트·타임라인·지도 핀·도시 스카이라인 등의 상징)"
    )

    prompt = f"""당신은 한국 B2B 매거진 일러스트 디렉터입니다. 아래 주간 인사이트의 커버 이미지를 만들 한국어 프롬프트 1개를 작성하세요.

목적: 사용자가 이 프롬프트를 그대로 DALL-E/클로드디자인 등에 입력 → 인사이트 페이지 hero 이미지로 사용.

콘텐츠 타입: {content_type}
타입별 시각 모티프: {type_brief}

비주얼 가이드 (필수 반영):
{style_brief}

작성 규칙:
- 한국어 한 단락. 3~5문장.
- 구체적인 시각 요소(객체/구도/색)를 명시.
- 이번 주 데이터의 색깔(어떤 분야가 강했는지 등)을 한두 단어로 반영.
- 금지: 영어 단어, 글자(이미지 안에 글자 넣지 말 것), 사람 얼굴, 사진풍.
- 응답은 프롬프트 본문만. 머리말/주석 X.

## 이번 주 인사이트 요지
{context}
"""
    return _claude_call(prompt).strip().strip('"').strip("'")


def write_market_narrative(stats: dict, monday, sunday, feedback: str | None = None) -> str:
    """시장 통계 → 3~5문장 한국어 narrative."""
    bsns_str = " / ".join(f"{k} {v}건" for k, v in stats["bsns_dist"][:3])
    top_inst = ", ".join(f"{k}({v})" for k, v in stats["top_institutions"][:3])
    wow = stats["wow_pct"]
    if wow is not None:
        wow_str = f"전주 대비 {wow:+.1f}%"
    elif stats["prev_total"]:
        wow_str = f"전주 표본 부족({stats['prev_total']}건)으로 비교 생략"
    else:
        wow_str = "전주 데이터 없음, 비교 생략"

    feedback_block = (
        f"\n\n## 직전 평가자 피드백 (반영 필수)\n{feedback}\n"
        if feedback
        else ""
    )

    prompt = f"""당신은 한국 공공조달 시장 동향 분석가입니다. 아래 주간 통계를 3~5문장 한 단락 한국어로 서술합니다.

규칙:
- 표·통계에서 제공된 수치만 사용. 새로운 숫자/추정 금지.
- 일반론 금지: "활발한 동향", "활발한 움직임", "반영하고 있다", "주목할 만한",
  "다양한 분야", "꾸준히 증가", "전반적으로". 발견되면 평가에서 컷.
- "전주 비교 생략"이라고 적혀 있으면 w/w 변동을 언급하지 말 것.
- 사실 두 개 이상을 한 문장으로 묶지 말고, 한 문장에 사실 하나씩.
- 끝맺음은 "~이다" 단호한 평어체.
- 응답은 본문만. 제목/머리말/마무리 안내 X.
{feedback_block}

## 기간
{monday.isoformat()} ~ {sunday.isoformat()}

## 통계
- 신규 공고 {stats['total']:,}건 ({wow_str})
- 업무구분: {bsns_str}
- TOP 발주기관: {top_inst}
- 평균 추정가: {format_amount(stats['avg_price'])}
- 중간값: {format_amount(stats['median_price'])}
"""
    text = _claude_call(prompt)
    # 코드펜스/머리말 제거
    text = text.strip().strip("`")
    if text.startswith("markdown\n"):
        text = text[len("markdown\n") :]
    return text.strip()
