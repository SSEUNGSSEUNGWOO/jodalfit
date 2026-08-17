"""주간 인사이트 파이프라인.

writer (claude CLI) → evaluator (codex CLI) → 통과 못 하면 피드백 재시도 → proofreader → 저장.

실행:
    cd backend
    uv run python -m jobs.weekly_insight.cli --type picks
    uv run python -m jobs.weekly_insight.cli --type market
    uv run python -m jobs.weekly_insight.cli --type picks --year-week 2026-w21
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from app.services.supabase_client import get_admin_client

from . import evaluator, proofreader, writer
from .fetchers import dedupe_by_no, fetch_window_notices
from .selectors import market_stats, pick_top10
from .templates import render_market, render_picks


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTENT_DIR = REPO_ROOT / "frontend" / "src" / "content" / "insights"


def iso_year_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-w{w:02d}"


def parse_year_week(s: str) -> tuple[date, date]:
    y, w = s.split("-w")
    monday = date.fromisocalendar(int(y), int(w), 1)
    return monday, monday + timedelta(days=6)


# ---------------------------------------------------------------------------

def run_picks(monday: date, sunday: date, base_slug: str) -> list[Path]:
    """통합 1편 발행 — 분야 다양성을 지키며 TOP 12 선별.

    (카테고리별 10편 분할은 거의 동일한 템플릿 글을 대량 생산해
    2026-08 폐기 — 두꺼운 1편이 독자에게도 검색엔진에도 낫다.)
    """
    client = get_admin_client()
    print(f"[picks] fetching notices {monday} ~ {sunday}...")
    raw = fetch_window_notices(client, monday, sunday)
    notices = dedupe_by_no(raw)
    print(f"[picks] {len(raw)} rows, {len(notices)} unique notices")

    today = date.today()
    picks = pick_top10(notices, today, count=12)
    if len(picks) < 5:
        print(f"[picks] 후보 {len(picks)}건 — 발행 임계 미달. 종료.")
        return []
    print(f"[picks] {len(picks)}건 선별")

    slug = f"{base_slug}-picks"
    feedback: str | None = None
    rubric = evaluator.load_rubric()
    max_retries = rubric.get("max_retries", 2)
    evaluation = None
    final_blurbs: list[str] = []

    print("[picks] Headline 생성")
    headline = writer.write_picks_headline(picks, monday, sunday, len(notices))
    print(f"[picks] title: {headline.get('title')}")

    for attempt in range(1, max_retries + 2):
        print(f"[picks] Writer 시도 {attempt}")
        final_blurbs = writer.write_picks_blurbs(picks, feedback=feedback)
        draft_md = render_picks(
            slug, monday, sunday, picks, final_blurbs, len(notices),
            None, headline=headline,
        )

        print(f"[picks] Evaluator 시도 {attempt}")
        evaluation = evaluator.evaluate(draft_md, content_type="picks")
        print(
            f"[picks] score={evaluation['weighted_score']} "
            f"pass={evaluation['pass']} scores={evaluation.get('scores')}"
        )
        if evaluation["pass"]:
            break
        feedback = evaluation.get("feedback") or ""
        if attempt > max_retries:
            print("[picks] 최대 재시도 초과. 마지막 draft로 발행.")
            break

    print("[picks] Image Prompt 생성")
    top_summary = "\n".join(
        f"- {p.get('bid_ntce_nm')} / {p.get('bsns_div_nm')} / "
        f"{p.get('dmnd_instt_nm') or p.get('ntce_instt_nm')}"
        for p in picks[:5]
    )
    image_prompt = writer.write_image_prompt(
        "picks",
        f"기간 {monday}~{sunday}, 검토할 만한 공고 TOP {len(picks)}.\n주요:\n{top_summary}",
    )

    md = render_picks(
        slug, monday, sunday, picks, final_blurbs, len(notices),
        evaluation, image_prompt, headline=headline,
    )

    print("[picks] Proofreader")
    md = proofreader.proofread(md)

    out = CONTENT_DIR / "picks" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"[picks] wrote {out}")
    return [out]


def run_market(monday: date, sunday: date, slug: str) -> Path:
    client = get_admin_client()
    print(f"[market] fetching notices {monday} ~ {sunday}...")
    raw = fetch_window_notices(client, monday, sunday)
    notices = dedupe_by_no(raw)

    prev_start = monday - timedelta(days=7)
    prev_end = sunday - timedelta(days=7)
    print(f"[market] fetching prev week {prev_start} ~ {prev_end}...")
    prev_raw = fetch_window_notices(client, prev_start, prev_end)
    prev_notices = dedupe_by_no(prev_raw)

    print(f"[market] this={len(notices)} prev={len(prev_notices)}")
    stats = market_stats(notices, prev_notices)

    # 정책 신호 — 국무회의·부처 발표 중 조달 관련 (웹 검색, 없으면 섹션 생략)
    print("[market] 정책 신호 수집 (웹 검색)")
    policy_signals = writer.write_policy_signals(monday, sunday)
    print(f"[market] 정책 신호: {'있음' if policy_signals else '없음(생략)'}")

    feedback: str | None = None
    rubric = evaluator.load_rubric()
    max_retries = rubric.get("max_retries", 2)
    evaluation = None
    md = ""

    final_narrative = ""
    for attempt in range(1, max_retries + 2):
        print(f"\n[market] === Writer 시도 {attempt} ===")
        final_narrative = writer.write_market_narrative(stats, monday, sunday, feedback=feedback)
        draft_md = render_market(
            slug, monday, sunday, stats, final_narrative, None,
            policy_signals=policy_signals,
        )

        print(f"[market] === Evaluator 시도 {attempt} ===")
        evaluation = evaluator.evaluate(draft_md, content_type="market")
        print(
            f"[market] score={evaluation['weighted_score']} "
            f"pass={evaluation['pass']} "
            f"scores={evaluation.get('scores')}"
        )
        print(f"[market] feedback: {evaluation.get('feedback', '')[:300]}")
        if evaluation["pass"]:
            break
        feedback = evaluation.get("feedback") or ""
        if attempt > max_retries:
            print("[market] 최대 재시도 초과. 마지막 draft로 발행.")
            break

    print("\n[market] === Image Prompt 생성 ===")
    bsns_summary = " / ".join(f"{k} {v}건" for k, v in stats["bsns_dist"][:3])
    top_inst = ", ".join(k for k, _ in stats["top_institutions"][:3])
    image_prompt = writer.write_image_prompt(
        "market",
        f"기간 {monday}~{sunday}, 신규 공고 {stats['total']:,}건. "
        f"업무구분: {bsns_summary}. 주요 발주기관: {top_inst}.",
    )
    print(f"[market] image_prompt: {image_prompt[:120]}...")

    md = render_market(
        slug, monday, sunday, stats, final_narrative, evaluation, image_prompt,
        policy_signals=policy_signals,
    )

    print("\n[market] === Proofreader ===")
    md = proofreader.proofread(md)

    out = CONTENT_DIR / "market" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"\n[market] wrote {out}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["picks", "market"], required=True)
    parser.add_argument("--year-week", help="2026-w22 (default: ISO of today)")
    args = parser.parse_args()

    slug = args.year_week or iso_year_week(date.today())
    monday, sunday = parse_year_week(slug)
    print(f"[cli] type={args.type} slug={slug} window={monday} ~ {sunday}")

    if args.type == "picks":
        run_picks(monday, sunday, slug)
    else:
        run_market(monday, sunday, slug)


if __name__ == "__main__":
    main()
