"""Markdown 렌더링. LLM이 생성한 blurb/narrative를 받아 frontmatter + 표와 결합."""

from __future__ import annotations

from datetime import date, datetime

from .selectors import format_amount


def _yaml_quote(s: str) -> str:
    """YAML 문자열용 안전 인용 (멀티라인 + 콜론 처리)."""
    if not s:
        return '""'
    if "\n" in s:
        return "|\n  " + s.replace("\n", "\n  ")
    return '"' + s.replace('"', '\\"') + '"'


def render_picks(
    slug: str,
    monday: date,
    sunday: date,
    picks: list[dict],
    blurbs: list[str],
    total_count: int,
    evaluation: dict | None = None,
    image_prompt: str | None = None,
    headline: dict | None = None,
) -> str:
    # 호별 고유 제목·요약 (writer 생성). 실패 시 템플릿 폴백.
    title = (headline or {}).get("title") or (
        f"이번 주 검토할 만한 공공입찰 {len(picks)}건"
    )
    summary = (headline or {}).get("summary") or (
        f"{monday.strftime('%Y년 %m월 %d일')} ~ {sunday.strftime('%m월 %d일')} 신규 공고 "
        f"{total_count:,}건 중 추정가 1억 이상 공고를 조달핏이 선별했습니다."
    )

    front_lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"summary: {_yaml_quote(summary)}",
        "type: picks",
        f"slug: {slug}",
        f"week_start: {monday.isoformat()}",
        f"week_end: {sunday.isoformat()}",
        f"published_at: {datetime.now().isoformat(timespec='seconds')}",
        f"total_notices: {total_count}",
        f"picks_count: {len(picks)}",
    ]
    if evaluation:
        front_lines.append(f"evaluation_score: {evaluation.get('weighted_score', 0)}")
    if image_prompt:
        front_lines.append(f"image_prompt: {_yaml_quote(image_prompt)}")
    front_lines.append("cover_image: \"\"")
    front_lines.append("---")
    front_lines.append("")
    front = "\n".join(front_lines)

    period = (
        f"{monday.strftime('%Y년 %m월 %d일')} ~ {sunday.strftime('%m월 %d일')} "
        f"신규 공고 {total_count:,}건 중 추정가 1억 이상, 기관·분야가 겹치지 않게 선별했습니다."
    )

    body = [f"# {title}\n", f"> {summary}\n", f"{period}\n"]
    for i, p in enumerate(picks, 1):
        # 공고기관(대행)과 수요기관이 다르면 둘 다 표기 — 제목 속 기관과의 혼선 방지
        dmnd = (p.get("dmnd_instt_nm") or "").strip()
        ntce = (p.get("ntce_instt_nm") or "").strip()
        if dmnd and ntce and dmnd != ntce:
            instt_line = f"- 수요기관: **{dmnd}** (공고: {ntce})"
        else:
            instt_line = f"- 기관: **{dmnd or ntce or '—'}**"
        bsns = p.get("bsns_div_nm") or "—"
        domain = p.get("_domain_label")
        bsns_line = f"{bsns} · {domain}" if domain else bsns
        price = format_amount(p.get("_price"))
        close = (p.get("bid_clse_date") or "")[:10]
        blurb = blurbs[i - 1] if i - 1 < len(blurbs) else ""

        body.append(f"## {i}. {p.get('bid_ntce_nm')}\n")
        if blurb:
            body.append(f"_{blurb}_\n")
        body.append(
            f"{instt_line}\n"
            f"- 구분: {bsns_line}\n"
            f"- 추정가: **{price}**\n"
            f"- 입찰 마감일: {close}\n"
            f"- 공고번호: [{p.get('bid_ntce_no')}](/notices/{p.get('bid_ntce_no')})\n"
        )

    body.append(
        "\n---\n\n"
        "## 우리 회사 기준으로 추천 받기\n\n"
        "위 공고들은 시장 전반에서 규모·기관 다양성 기준으로 선별한 것입니다. "
        "회사 등록업종·공급물품·수주 이력에 맞춘 개인화 추천은 [홈에서 회사명을 입력](/)하시면 받을 수 있습니다. "
        "마감일이 지난 공고는 각 공고 페이지에서 낙찰·계약 단계로 이어집니다.\n"
    )
    return front + "\n".join(body)


def render_market(
    slug: str,
    monday: date,
    sunday: date,
    stats: dict,
    narrative: str,
    evaluation: dict | None = None,
    image_prompt: str | None = None,
    policy_signals: str = "",
) -> str:
    title = (
        f"공공조달 주간 동향 — {monday.strftime('%m월 %d일')}"
        f"~{sunday.strftime('%m월 %d일')}"
    )
    wow = stats["wow_pct"]
    if wow is not None:
        wow_str = f"{wow:+.1f}% (w/w)"
    elif stats["prev_total"]:
        wow_str = f"전주 표본 부족({stats['prev_total']}건, 비교 생략)"
    else:
        wow_str = "전주 데이터 없음"
    summary = (
        f"{monday.strftime('%Y년 %m월 %d일')} ~ {sunday.strftime('%m월 %d일')} "
        f"나라장터 신규 공고 {stats['total']:,}건, {wow_str}."
    )

    front_lines = [
        "---",
        f'title: "{title}"',
        f'summary: "{summary}"',
        "type: market",
        f"slug: {slug}",
        f"week_start: {monday.isoformat()}",
        f"week_end: {sunday.isoformat()}",
        f"published_at: {datetime.now().isoformat(timespec='seconds')}",
        f"total_notices: {stats['total']}",
        f"prev_total: {stats['prev_total']}",
    ]
    if evaluation:
        front_lines.append(f"evaluation_score: {evaluation.get('weighted_score', 0)}")
    if image_prompt:
        front_lines.append(f"image_prompt: {_yaml_quote(image_prompt)}")
    front_lines.append("cover_image: \"\"")
    # market 차트 데이터 (frontend 차트 컴포넌트가 그대로 사용)
    front_lines.append("chart_bsns:")
    for k, v in stats["bsns_dist"]:
        front_lines.append(f'  - {{ label: "{k}", value: {v} }}')
    front_lines.append("chart_price:")
    for k, v in stats["price_buckets"].items():
        front_lines.append(f'  - {{ label: "{k}", value: {v} }}')
    front_lines.append("---")
    front_lines.append("")
    front = "\n".join(front_lines)

    if wow is not None:
        glance_wow = f"전주 대비 {wow:+.1f}%"
    elif stats["prev_total"]:
        glance_wow = f"전주 표본 부족 ({stats['prev_total']}건)"
    else:
        glance_wow = "전주 데이터 없음"

    lines = [
        f"# {title}\n",
        f"> {summary}\n",
        "## 한눈에\n",
        f"- 신규 공고: **{stats['total']:,}건** · {glance_wow}",
        f"- 평균 추정가: **{format_amount(stats['avg_price'])}** · 중간값 {format_amount(stats['median_price'])}",
        f"- 예산 표시 공고: {stats['price_sample_count']:,}건\n",
        "## 업무구분 분포\n",
        "| 업무구분 | 공고 수 | 비중 |",
        "| --- | ---: | ---: |",
    ]
    for k, v in stats["bsns_dist"]:
        pct = (v / stats["total"] * 100) if stats["total"] else 0
        lines.append(f"| {k} | {v:,} | {pct:.1f}% |")

    lines.append("\n## 발주 기관 TOP 10\n")
    lines.append("| 순위 | 기관 | 공고 수 |")
    lines.append("| ---: | --- | ---: |")
    for i, (k, v) in enumerate(stats["top_institutions"], 1):
        lines.append(f"| {i} | {k} | {v} |")

    lines.append("\n## 예산 규모 분포\n")
    lines.append("| 구간 | 공고 수 |")
    lines.append("| --- | ---: |")
    for k, v in stats["price_buckets"].items():
        lines.append(f"| {k} | {v:,} |")

    lines.append("\n## 이번 주 한 단락\n")
    lines.append(narrative)

    # 정책 신호 — 국무회의·부처 발표 중 조달 관련만, 출처 포함 사실 인용
    if policy_signals:
        lines.append("\n## 정책 신호\n")
        lines.append(
            "_이번 주 정부 발표 중 공공조달·발주와 연결되는 것만 추렸습니다. "
            "발표 내용은 출처 원문 기준이며, 시사점은 조달 관점의 참고 의견입니다._\n"
        )
        lines.append(policy_signals)

    lines.append(
        "\n---\n\n"
        "## 분석 데이터\n\n"
        "나라장터 8개 OpenAPI 기준, jodalfit이 매일 자동 수집한 신규 공고를 집계했습니다. "
        "특정 회사·업종에 맞춘 추천은 [홈에서 회사명을 입력](/)하면 받을 수 있습니다."
    )

    return front + "\n".join(lines) + "\n"
