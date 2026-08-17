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


def _claude_call(prompt: str, allow_web_search: bool = False) -> str:
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    claude_cmd = shutil.which("claude") or "claude"
    args = [claude_cmd, "-p", "-"]
    if allow_web_search:
        args += ["--allowedTools", "WebSearch"]
    result = subprocess.run(
        args,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT * (2 if allow_web_search else 1),
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
    """공고 N건 → 12~25자 blurb N개 (JSON 한 번 호출)."""
    items_json = json.dumps(
        [
            {
                "i": i + 1,
                "nm": p.get("bid_ntce_nm"),
                "bsns": p.get("bsns_div_nm"),
                "instt": p.get("dmnd_instt_nm") or p.get("ntce_instt_nm"),
                "price": format_amount(p.get("_price")),
                "domain": p.get("_domain_label"),
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

    prompt = f"""당신은 한국 공공조달 큐레이션 에디터입니다. 공고 {len(picks)}건에 각각 12~25자 한국어 한 줄 blurb을 답니다.

규칙:
- 사실 기반, 추측 금지, 헤지 표현 금지 ("~할 가능성", "~로 보입니다")
- 공허한 일반론 금지 ("활발한", "주목할 만한", "다양한")
- 마감 잔여 일수(D-n, "마감 N일") 언급 금지 — 이 글은 아카이브로도 읽히므로 발행 후에도 유효한 문장만
- 제목을 그대로 줄이지 말고, 규모/발주 배경/도메인 텍스처 중 1개를 골라 한 줄
- 톤: jodalfit은 "검토할 만한" 디스커버리. "따낼 만한" 금지.
- 좋은 예: "70억 규모 공공 클라우드 네이티브 전환"
           "군 실증용 GPU 리스, 물품 발주로는 드문 규모"
- 나쁜 예: "주목할 만한 공고, 검토 필요"
           "마감 여유 11일" (잔여 일수 금지)

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


def write_picks_headline(
    picks: list[dict], monday, sunday, total_count: int
) -> dict:
    """호별 고유 제목·요약 생성 — 매주 같은 템플릿 제목을 피한다."""
    top_summary = "\n".join(
        f"- {p.get('bid_ntce_nm')} / {p.get('_domain_label') or p.get('bsns_div_nm')} / "
        f"{format_amount(p.get('_price'))} / {p.get('dmnd_instt_nm') or p.get('ntce_instt_nm')}"
        for p in picks[:6]
    )
    prompt = f"""당신은 한국 공공조달 주간지 에디터입니다. 이번 호 픽 기사의 제목과 요약을 씁니다.

규칙:
- title: 25~45자. 이번 주 픽의 실제 내용(대표 공고·규모·분야 흐름)이 드러나는 고유한 제목.
  "이번 주 픽:" 으로 시작. 예) "이번 주 픽: 클라우드 전환 70억부터 치안 데이터셋까지 12건"
- summary: 1~2문장, 90자 이내. 기간과 선별 기준(신규 {total_count:,}건 중 추정가 1억 이상)을 자연스럽게 포함.
- 사실만. 과장·추측·"주목할 만한" 류 금지. 마감 잔여 일수 금지.
- 응답: JSON만. 형식: {{"title":"...","summary":"..."}}

## 기간
{monday.isoformat()} ~ {sunday.isoformat()}

## 이번 주 픽 (상위)
{top_summary}
"""
    raw = _claude_call(prompt)
    parsed = _extract_json(raw)
    return {
        "title": str(parsed.get("title", "")).strip(),
        "summary": str(parsed.get("summary", "")).strip(),
    }


def write_policy_signals(monday, sunday) -> str:
    """정책 신호 섹션 — 해당 주 국무회의·부처 발표 중 조달 관련만 웹 검색으로 수집.

    원칙: 발언·발표는 출처와 함께 사실만 인용, 해석은 조달 관점 한 줄로 한정.
    관련 소식이 없으면 빈 문자열(섹션 생략).
    """
    prompt = f"""당신은 한국 공공조달 주간지의 정책 담당 에디터입니다. 웹 검색을 사용해 아래 기간의 정책 소식 중 "공공조달·정부 발주에 영향을 줄 만한 것"만 찾아 정리하세요.

검색 대상 (이 기간: {monday.isoformat()} ~ {sunday.isoformat()}):
- 국무회의 결과, 대통령·총리 주재 회의 발표
- 기획재정부·행정안전부·과기정통부·조달청 보도자료
- 추경·예산 편성, 신규 국가사업 발표

작성 규칙:
- 0~3건. 조달·발주와의 연결이 뚜렷한 것만. 없으면 정확히 "NONE"만 출력.
- 건당 형식: "**[발표 주체·날짜]** 사실 요약 1문장. → 조달 관점 시사점 1문장. ([출처명](URL))"
- 발언 인용은 사실 그대로, 정치적 평가·논평 절대 금지.
- 확인 안 되는 내용은 쓰지 않는다. 추측·전망 남발 금지 ("~할 것으로 보인다" 최대 1회).
- 응답은 마크다운 리스트 본문만. 머리말 X.
"""
    try:
        text = _claude_call(prompt, allow_web_search=True).strip()
    except Exception:
        return ""
    if not text or text.upper().startswith("NONE"):
        return ""
    return text


def write_image_prompt(content_type: str, context: str) -> str:
    """주간 인사이트 커버 이미지용 한국어 프롬프트 생성.

    사용자가 이 프롬프트를 외부 도구(클로드 디자인/DALL-E/Imagen 등)에 그대로 넣어
    이미지를 만들고 frontmatter `cover_image:` 경로에 직접 등록.
    """
    style_brief = (
        "조달핏 비주얼 가이드(청색 장부 세계): 차가운 흰 장부지 배경, 미니멀, 큰 여백, "
        "주조색은 네이비(#1E3A66), 포인트는 인주 레드(#B23A2A) 한 곳만, "
        "괘선(가는 가로줄)·도장·문서 모티프 환영, "
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
