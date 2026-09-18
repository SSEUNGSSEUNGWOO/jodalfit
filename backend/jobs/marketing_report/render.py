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
        p = nv.get("parsed") or {}
        pn = dig(prev_week, "naver.parsed") or {}
        if p:
            out.append(_table(H, [
                (k, v, pn.get(k, "—"), f"{v - pn[k]:+,}" if isinstance(pn.get(k), (int, float)) else "—")
                for k, v in p.items()
            ]))
            out.append("")
            out.append("_키 이름 추정값 — 파서 확정 전 (README '네이버 파서 확정')_")
        else:
            out.append(f"_덤프 {nv['dumps']}개 저장({nv['dump_dir']}), 파서 미확정이라 숫자 없음_")
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
    out.append("## 6. 키워드 추적 (구글 평균 순위, 직전 스냅샷 대비)")
    tracked = dig(snap, "gsc.search.tracked")
    if tracked:
        mv = keyword_moves(tracked, dig(prev_day, "gsc.search.tracked"))
        def fmt(items, f):
            return ", ".join(f(*i) for i in items) if items else "없음"
        out.append(f"- 상승: {fmt(mv['up'], lambda q, a, b: f'{q} ({a}→{b})')}")
        out.append(f"- 하락: {fmt(mv['down'], lambda q, a, b: f'{q} ({a}→{b})')}")
        out.append(f"- 신규: {fmt(mv['new'], lambda q, b: f'{q} ({b})')}")
        out.append(f"- 이탈: {fmt(mv['lost'], lambda q, a: f'{q} (전 {a})')}")
        out.append(f"- 유지: {fmt(mv['flat'], lambda q, b: f'{q} ({b})')}")
        out.append(f"- 노출 없음: {len(mv['absent'])}/{len(tracked)}개")
    else:
        out.append("_미수집 (서치콘솔 데이터 없음)_")
    out.append("")

    out.append("## 수집 상태")
    out.append(_table(("소스", "상태"), [(k, v) for k, v in src.items()]))
    out.append("")
    return "\n".join(out)
