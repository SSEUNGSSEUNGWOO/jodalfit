"""일일 마케팅 성적표 CLI.

    uv run python -m jobs.marketing_report.cli                # 어제(KST) 성적표
    uv run python -m jobs.marketing_report.cli --date 2026-09-17
    uv run python -m jobs.marketing_report.cli --skip naver,gsc   # 일부 소스 건너뛰기
    uv run python -m jobs.marketing_report.cli --naver-login      # 네이버 로그인 1회 (창 뜸)
    uv run python -m jobs.marketing_report.cli --no-interpret     # LLM 해석 생략

출력: docs/marketing/reports/YYYY-MM-DD.md, 스냅샷 docs/marketing/snapshots/YYYY-MM-DD.json (비교용, 커밋 대상).
소스 하나가 실패해도 나머지로 성적표를 낸다 — 실패 사유는 "수집 상태" 표에 남는다.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import gsc, naver, supabase_metrics
from .compare import REPO_ROOT, latest_snapshot_before, load_snapshot, save_snapshot
from .interpret import interpret
from .render import render

CONFIG = Path(__file__).with_name("config.yaml")
REPORT_DIR = REPO_ROOT / "docs" / "marketing" / "reports"
KST = timezone(timedelta(hours=9))


def _try(sources: dict, key: str, fn):
    try:
        v = fn()
        sources[key] = "ok"
        return v
    except Exception as e:  # 소스 하나 때문에 성적표를 못 내지 않는다
        sources[key] = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"  ! {key}: {sources[key]}")
        return None


def run(day: date, skip: set[str], do_interpret: bool) -> Path:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    site, domain = cfg["site"]["gsc_site_url"], cfg["site"]["domain"]
    keywords = [k["q"] for k in cfg["keywords"]]
    sources: dict[str, str] = {}
    snap: dict = {"date": day.isoformat(), "domain": domain, "sources": sources}
    # 같은 날짜를 다시 돌릴 때 --skip 한 소스는 기존 스냅샷 값을 유지한다 (덮어써서 지우지 않게)
    existing = load_snapshot(day) or {}
    carry = {"gsc": ("gsc", ("gsc_search", "gsc_sitemaps", "gsc_inspect")),
             "naver": ("naver", ("naver",)), "supabase": ("supabase", ("supabase",))}
    for src_name in skip:
        key, status_keys = carry.get(src_name, (None, ()))
        if key and existing.get(key) is not None:
            snap[key] = existing[key]
            for sk in status_keys:
                sources[sk] = f"{existing.get('sources', {}).get(sk, 'ok')} (이전 실행 유지)"
    print(f"[marketing_report] {day}")

    if "gsc" not in skip:
        search = _try(sources, "gsc_search", lambda: gsc.collect_search(site, day, cfg["page_types"], keywords))
        sitemaps = _try(sources, "gsc_sitemaps", lambda: gsc.collect_sitemaps(site))
        urls = _try(sources, "gsc_inspect", lambda: supabase_metrics.sample_urls(domain, cfg["index_sample"]))
        sample = _try(sources, "gsc_inspect", lambda: gsc.inspect_urls(site, urls)) if urls else None
        snap["gsc"] = {"search": search, "sitemaps": sitemaps, "index_sample": sample}
    else:
        for k in ("gsc_search", "gsc_sitemaps", "gsc_inspect"):
            sources.setdefault(k, "skipped")

    if "naver" not in skip:
        snap["naver"] = _try(sources, "naver", lambda: naver.collect(f"https://{domain}", day, cfg["page_types"], keywords))
    else:
        sources.setdefault("naver", "skipped")

    if "supabase" not in skip:
        snap["supabase"] = _try(sources, "supabase", lambda: supabase_metrics.daily_stats(day))
    else:
        sources.setdefault("supabase", "skipped")

    prev_week = load_snapshot(day - timedelta(days=7))
    prev_day = latest_snapshot_before(day)
    save_snapshot(day, snap)

    table_md = render(snap, prev_week, prev_day, None)
    interpretation = _try(sources, "interpret", lambda: interpret(table_md)) if do_interpret else None
    md = render(snap, prev_week, prev_day, interpretation)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{day.isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"[marketing_report] wrote {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 어제, KST)")
    ap.add_argument("--skip", default="", help="건너뛸 소스: gsc,naver,supabase")
    ap.add_argument("--naver-login", action="store_true", help="네이버 로그인 창 열기 (1회)")
    ap.add_argument("--no-interpret", action="store_true")
    args = ap.parse_args()

    if args.naver_login:
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        naver.login(cfg["site"]["naver_console"])
        raise SystemExit(0)

    d = date.fromisoformat(args.date) if args.date else (datetime.now(KST).date() - timedelta(days=1))
    run(d, {s.strip() for s in args.skip.split(",") if s.strip()}, not args.no_interpret)
