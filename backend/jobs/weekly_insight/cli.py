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
from .selectors import DOMAIN_LABELS, market_stats, pick_top_by_category
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

def _run_picks_for_category(
    monday: date,
    sunday: date,
    base_slug: str,
    domain: str,
    label: str,
    picks: list[dict],
    total_notices: int,
) -> Path:
    """단일 카테고리 발행. writer → evaluator (재시도) → image → proofreader → 저장."""
    slug = f"{base_slug}-picks-{domain}"
    print(f"\n[picks/{domain}] {label} — {len(picks)}건")

    feedback: str | None = None
    rubric = evaluator.load_rubric()
    max_retries = rubric.get("max_retries", 2)
    evaluation = None
    final_blurbs: list[str] = []

    for attempt in range(1, max_retries + 2):
        print(f"[picks/{domain}] Writer 시도 {attempt}")
        final_blurbs = writer.write_picks_blurbs(picks, feedback=feedback)
        draft_md = render_picks(
            slug, monday, sunday, picks, final_blurbs, total_notices,
            None, category_label=label,
        )

        print(f"[picks/{domain}] Evaluator 시도 {attempt}")
        evaluation = evaluator.evaluate(draft_md, content_type="picks")
        print(
            f"[picks/{domain}] score={evaluation['weighted_score']} "
            f"pass={evaluation['pass']} scores={evaluation.get('scores')}"
        )
        if evaluation["pass"]:
            break
        feedback = evaluation.get("feedback") or ""
        if attempt > max_retries:
            print(f"[picks/{domain}] 최대 재시도 초과. 마지막 draft로 발행.")
            break

    print(f"[picks/{domain}] Image Prompt 생성")
    top_summary = "\n".join(
        f"- {p.get('bid_ntce_nm')} / {p.get('bsns_div_nm')} / "
        f"{p.get('dmnd_instt_nm') or p.get('ntce_instt_nm')}"
        for p in picks[:5]
    )
    image_prompt = writer.write_image_prompt(
        "picks",
        f"기간 {monday}~{sunday}, {label} 분야 TOP {len(picks)}.\n주요:\n{top_summary}",
    )

    md = render_picks(
        slug, monday, sunday, picks, final_blurbs, total_notices,
        evaluation, image_prompt, category_label=label,
    )

    print(f"[picks/{domain}] Proofreader")
    md = proofreader.proofread(md)

    out = CONTENT_DIR / "picks" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"[picks/{domain}] wrote {out}")
    return out


def run_picks(monday: date, sunday: date, slug: str) -> list[Path]:
    """카테고리별 TOP 5 발행. 카테고리 후보 <5면 스킵."""
    client = get_admin_client()
    print(f"[picks] fetching notices {monday} ~ {sunday}...")
    raw = fetch_window_notices(client, monday, sunday)
    notices = dedupe_by_no(raw)
    print(f"[picks] {len(raw)} rows, {len(notices)} unique notices")

    today = date.today()
    by_domain = pick_top_by_category(notices, today, per_cat=5, min_cat=5)

    if not by_domain:
        print("[picks] 발행할 카테고리 없음 (모두 후보 <5). 종료.")
        return []

    print(f"[picks] 발행 카테고리 {len(by_domain)}개: "
          f"{', '.join(f'{d}({len(p)})' for d, p in by_domain.items())}")

    outputs: list[Path] = []
    for domain, picks in by_domain.items():
        label = DOMAIN_LABELS[domain]
        try:
            out = _run_picks_for_category(
                monday, sunday, slug, domain, label, picks, len(notices),
            )
            outputs.append(out)
        except Exception as e:
            print(f"[picks/{domain}] 실패: {e}")
            continue

    print(f"\n[picks] 완료: {len(outputs)}개 카테고리 발행")
    return outputs


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

    feedback: str | None = None
    rubric = evaluator.load_rubric()
    max_retries = rubric.get("max_retries", 2)
    evaluation = None
    md = ""

    final_narrative = ""
    for attempt in range(1, max_retries + 2):
        print(f"\n[market] === Writer 시도 {attempt} ===")
        final_narrative = writer.write_market_narrative(stats, monday, sunday, feedback=feedback)
        draft_md = render_market(slug, monday, sunday, stats, final_narrative, None)

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

    md = render_market(slug, monday, sunday, stats, final_narrative, evaluation, image_prompt)

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
