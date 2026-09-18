"""스냅샷 + 비교 결과 → 마크다운. 여섯 칸: 색인·크롤(구글) / 구글 검색 유입 / 네이버 / 사람 행동 / 제품 건강 / 키워드."""

from __future__ import annotations

from .compare import dig, keyword_moves, row


def _table(header: tuple[str, ...], rows: list[tuple]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _pct(num, den) -> str:
    return "—" if not den else f"{num / den * 100:.0f}%"


def render(snap: dict, prev_week: dict | None, prev_day: dict | None, interpretation: str | None) -> str:
    day = snap["date"]
    src = snap["sources"]
    gsc, sb, nv = snap.get("gsc"), snap.get("supabase"), snap.get("naver")
    H = ("지표", day, "전주 같은 요일", "변화")
    out = [f"# 조달핏 마케팅 성적표 — {day}", ""]

    out.append("## 한 줄 해석")
    out.append(interpretation or "_해석 생략_")
    out.append("")

    # 1. 색인·크롤 (구글)
    out.append("## 1. 색인·크롤 (구글)")
    if gsc and gsc.get("index_sample"):
        s = gsc["index_sample"]
        ps = dig(prev_week, "gsc.index_sample")
        out.append(_table(H, [
            ("표본 색인 비율", _pct(s["indexed"], s["sampled"]), _pct(ps["indexed"], ps["sampled"]) if ps else "—",
             f"{s['indexed'] - ps['indexed']:+d}건" if ps else "—"),
            ("표본 수", s["sampled"], ps["sampled"] if ps else "—", ""),
        ]))
        out.append("")
        out.append("상태별: " + ", ".join(f"{k} {v}" for k, v in sorted(s["by_state"].items(), key=lambda x: -x[1])))
    else:
        out.append(f"_미수집 — {src.get('gsc_inspect', '')}_")
    if gsc and gsc.get("sitemaps"):
        out.append("")
        out.append(_table(("사이트맵", "제출", "색인", "오류", "경고", "마지막 다운로드"),
                          [(m["path"].replace(f"https://{snap['domain']}", ""), m["submitted"], m["indexed"], m["errors"], m["warnings"], m["last_downloaded"])
                           for m in gsc["sitemaps"]]))
    out.append("")

    # 2. 구글 검색 유입
    out.append("## 2. 구글 검색 유입")
    if gsc and gsc.get("search") and gsc["search"].get("data_date"):
        g = gsc["search"]
        note = f" (데이터 기준일 {g['data_date']})" if g["data_date"] != day else ""
        out.append(f"기준일{note}" if note else "")
        out.append(_table(H, [
            row("클릭", snap, prev_week, "gsc.search.clicks"),
            row("노출", snap, prev_week, "gsc.search.impressions"),
            row("CTR %", snap, prev_week, "gsc.search.ctr", "{:.2f}"),
            row("평균 순위", snap, prev_week, "gsc.search.position", "{:.1f}"),
        ]))
        if g["by_type"]:
            out.append("")
            out.append(_table(("페이지 유형", "클릭", "노출"),
                              [(k, v["clicks"], v["impressions"]) for k, v in sorted(g["by_type"].items(), key=lambda x: -x[1]["impressions"])]))
        if g["top_queries"]:
            out.append("")
            out.append(_table(("상위 검색어", "클릭", "노출", "순위"),
                              [(q["query"], q["clicks"], q["impressions"], q["position"]) for q in g["top_queries"][:10]]))
    else:
        out.append(f"_미수집 — {src.get('gsc_search', '')}_")
    out.append("")

    # 3. 네이버 서치어드바이저
    out.append("## 3. 네이버 서치어드바이저")
    if nv:
        if nv.get("data_date"):
            out.append(_table(H, [
                row("클릭", snap, prev_week, "naver.clicks"),
                row("노출", snap, prev_week, "naver.impressions"),
                row("CTR %", snap, prev_week, "naver.ctr", "{:.1f}"),
            ]))
        else:
            out.append("_이 날짜의 노출·클릭 데이터 없음 (네이버 집계 지연)_")
        out.append("")
        idx_rows = []
        if nv.get("index"):
            idx_rows += [
                row(f"색인 페이지 (진단 {nv['index']['date']})", snap, prev_week, "naver.index.indexed"),
                row("수집제한", snap, prev_week, "naver.index.crawl_limited"),
                row("색인제외", snap, prev_week, "naver.index.index_excluded"),
            ]
        if nv.get("crawl"):
            idx_rows += [
                row("수집 페이지", snap, prev_week, "naver.crawl.pages"),
                row("수집 오류", snap, prev_week, "naver.crawl.errors"),
            ]
        if idx_rows:
            out.append(_table(H, idx_rows))
            out.append("")
        if nv.get("by_type_top"):
            out.append(f"페이지 유형별 (최신일 {nv.get('top_date')}, 클릭 상위 URL 50개 기준)")
            out.append(_table(("페이지 유형", "클릭", "노출"),
                              [(k, v["clicks"], v["impressions"]) for k, v in sorted(nv["by_type_top"].items(), key=lambda x: -x[1]["clicks"])]))
            out.append("")
        if nv.get("top_queries"):
            out.append(f"상위 검색어 (최신일 {nv.get('top_date')})")
            out.append(_table(("검색어", "클릭", "노출", "순위"),
                              [(q["query"], q["clicks"], q["impressions"], q["position"]) for q in nv["top_queries"][:10]]))
    else:
        out.append(f"_미수집 — {src.get('naver', '')}_")
    out.append("")

    # 4. 사람 행동 (Supabase)
    out.append("## 4. 사람 행동")
    if sb:
        ev, pev = sb.get("events") or {}, (dig(prev_week, "supabase.events") or {})
        ret = _pct(sb["returning_companies"], sb["unique_companies"])
        pret = _pct(dig(prev_week, "supabase.returning_companies") or 0, dig(prev_week, "supabase.unique_companies") or 0) if prev_week else "—"
        out.append(_table(H, [
            row("사람 검색 (SSR 제외)", snap, prev_week, "supabase.human_searches"),
            row("회사 검색 중 식별 성공", snap, prev_week, "supabase.company_identified"),
            ("재검색율 (7일 내 재검색 회사 / 오늘 검색 회사)", ret, pret, ""),
            row("검색된 회사 수", snap, prev_week, "supabase.unique_companies"),
            ("공고 클릭", ev.get("click", 0), pev.get("click", "—") if prev_week else "—", ""),
            ("공고 저장", ev.get("save", 0), pev.get("save", "—") if prev_week else "—", ""),
            row("구독 신청", snap, prev_week, "supabase.subscribers_new"),
            row("구독 인증 완료", snap, prev_week, "supabase.subscribers_verified"),
            row("이메일 캡처", snap, prev_week, "supabase.email_subscribers_new"),
            row("SSR 호출 (참고: 크롤러 유발)", snap, prev_week, "supabase.ssr_searches"),
        ]))
    else:
        out.append(f"_미수집 — {src.get('supabase', '')}_")
    out.append("")

    # 5. 제품 건강
    out.append("## 5. 제품 건강")
    if sb:
        n = sb["human_searches"] or 0
        pn = dig(prev_week, "supabase.human_searches") or 0
        out.append(_table(H, [
            ("오류율", _pct(sb["errors"], n), _pct(dig(prev_week, "supabase.errors") or 0, pn) if prev_week else "—", ""),
            ("결과 0건 비율", _pct(sb["zero_results"], n), _pct(dig(prev_week, "supabase.zero_results") or 0, pn) if prev_week else "—", ""),
            row("p50 응답 ms", snap, prev_week, "supabase.p50_latency_ms", "{:,.0f}"),
        ]))
    else:
        out.append("_미수집_")
    out.append("")

    # 6. 키워드 추적
    out.append("## 6. 키워드 추적 (평균 순위, 직전 스냅샷 대비)")
    kw = snap.get("keywords") or {}
    auto = set(kw.get("auto", []))
    if kw:
        out.append(f"수동 {len(kw.get('manual', []))}개 + 자동 {len(auto)}개. 자동은 `*` 표시 "
                   "(네이버 7일 누적 클릭 2회 이상 또는 14일 중 2일 이상 상위 검색어).")
        out.append(f"- 오늘 자동 추가: {', '.join(kw.get('added') or []) or '없음'}")
        out.append(f"- 오늘 자동 제외: {', '.join(kw.get('dropped') or []) or '없음'}")
        out.append("")
    def name(q):
        return f"{q}*" if q in auto else q
    def fmt(items, f):
        return ", ".join(f(*i) for i in items) if items else "없음"
    for label, path, note in (("네이버", "naver.tracked", "최신일 상위 검색어 50개 안에 든 것만 잡힘"),
                              ("구글", "gsc.search.tracked", "")):
        tracked = dig(snap, path)
        out.append(f"### {label}" + (f" _({note})_" if note else ""))
        if not tracked:
            out.append("_미수집_")
            continue
        mv = keyword_moves(tracked, dig(prev_day, path))
        out.append(f"- 상승: {fmt(mv['up'], lambda q, a, b: f'{name(q)} ({a}→{b})')}")
        out.append(f"- 하락: {fmt(mv['down'], lambda q, a, b: f'{name(q)} ({a}→{b})')}")
        out.append(f"- 신규: {fmt(mv['new'], lambda q, b: f'{name(q)} ({b})')}")
        out.append(f"- 이탈: {fmt(mv['lost'], lambda q, a: f'{name(q)} (전 {a})')}")
        out.append(f"- 유지: {fmt(mv['flat'], lambda q, b: f'{name(q)} ({b})')}")
        absent_manual = sum(1 for q in mv["absent"] if q not in auto)
        absent_auto = len(mv["absent"]) - absent_manual
        out.append(f"- 노출 없음: 수동 {absent_manual}/{len(tracked) - len(auto & set(tracked))}개, "
                   f"자동 {absent_auto}/{len(auto & set(tracked))}개")
    out.append("")

    out.append("## 수집 상태")
    out.append(_table(("소스", "상태"), [(k, v) for k, v in src.items()]))
    out.append("")
    return "\n".join(out)
