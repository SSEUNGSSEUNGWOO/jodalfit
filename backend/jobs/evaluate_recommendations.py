"""추천 품질 정성 평가용 배치 리포트.

3개 버킷 × N개 회사로 추천 결과를 마크다운 리포트로 묶음:
- 콜드스타트 (수주 0건, 업종 벡터만)
- 균형 (수주 1~5건)
- 풍부 (수주 6건+)

각 회사마다 추천 TOP 5 + 자동 메트릭 (업무구분 일치/매칭 점수/기관 다양성).
사용자가 한 번에 검토하고 알고리즘 튜닝 신호 잡기.

실행:
    cd backend
    uv run python -m jobs.evaluate_recommendations
    uv run python -m jobs.evaluate_recommendations --per-bucket 5
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.services.recommend import recommend
from app.services.supabase_client import get_admin_client


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "backend" / "data" / "eval"


def fetch_contract_counts(client) -> dict[str, int]:
    """contracts 테이블에서 bizrno_norm별 카운트 직접 집계.
    companies.contract_count 컬럼은 채워지지 않은 죽은 컬럼이라 신뢰 못 함.
    """
    counter: Counter = Counter()
    offset = 0
    PAGE = 1000
    while True:
        r = (
            client.table("contracts")
            .select("rprsnt_corp_bizrno_norm")
            .not_.is_("rprsnt_corp_bizrno_norm", "null")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not r:
            break
        for row in r:
            v = row.get("rprsnt_corp_bizrno_norm")
            if v:
                counter[v] += 1
        if len(r) < PAGE:
            break
        offset += PAGE
    return dict(counter)


def fetch_candidate_companies(client) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    PAGE = 1000
    while len(rows) < 4000:
        r = (
            client.table("companies")
            .select(
                "bizrno,bizrno_norm,corp_nm,corp_bsns_div_nm,mnfctr_div_nm,rgn_nm,is_restricted"
            )
            .not_.is_("embedding", "null")
            .not_.is_("bizrno_norm", "null")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not r:
            break
        rows.extend(r)
        if len(r) < PAGE:
            break
        offset += PAGE
    return [r for r in rows if not r.get("is_restricted")]


def fetch_industries(client, bizrnos: list[str]) -> dict[str, list[str]]:
    """회사별 등록업종 (대표 업종 먼저)."""
    out: dict[str, list[str]] = {b: [] for b in bizrnos}
    PAGE = 500
    for i in range(0, len(bizrnos), PAGE):
        sub = bizrnos[i : i + PAGE]
        r = (
            client.table("company_industries")
            .select("bizrno,indstryty_nm,rprsnt_indstryty_yn")
            .in_("bizrno", sub)
            .execute()
            .data
        )
        for row in r:
            b = row["bizrno"]
            nm = row.get("indstryty_nm")
            if not nm:
                continue
            if row.get("rprsnt_indstryty_yn") == "Y":
                out.setdefault(b, []).insert(0, nm)
            else:
                out.setdefault(b, []).append(nm)
    return out


def fetch_supply_products(client, bizrnos: list[str]) -> dict[str, list[str]]:
    """회사별 공급물품 (대표 먼저)."""
    out: dict[str, list[str]] = {b: [] for b in bizrnos}
    PAGE = 500
    for i in range(0, len(bizrnos), PAGE):
        sub = bizrnos[i : i + PAGE]
        r = (
            client.table("company_supply_products")
            .select("bizrno,dtl_prdct_clsfc_nm,rprsnt_prdct_yn")
            .in_("bizrno", sub)
            .execute()
            .data
        )
        for row in r:
            b = row["bizrno"]
            nm = row.get("dtl_prdct_clsfc_nm")
            if not nm:
                continue
            if row.get("rprsnt_prdct_yn") == "Y":
                out.setdefault(b, []).insert(0, nm)
            else:
                out.setdefault(b, []).append(nm)
    return out


def pick_diverse(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    rng.shuffle(pool)
    out: list[dict] = []
    seen = set()
    for r in pool:
        div = r.get("corp_bsns_div_nm") or "—"
        if div in seen:
            continue
        out.append(r)
        seen.add(div)
        if len(out) >= n:
            break
    for r in pool:
        if len(out) >= n:
            break
        if r not in out:
            out.append(r)
    return out[:n]


def sample_by_bucket(
    pool: list[dict],
    contract_counts: dict[str, int],
    per_bucket: int,
    rng: random.Random,
) -> dict[str, list[dict]]:
    cold, bal, rich = [], [], []
    for r in pool:
        c = contract_counts.get(r["bizrno_norm"], 0)
        r["_suju"] = c  # downstream render에서 사용
        if c == 0:
            cold.append(r)
        elif c <= 5:
            bal.append(r)
        else:
            rich.append(r)
    return {
        "cold (수주 0건, 업종 100%)": pick_diverse(cold, per_bucket, rng),
        "balanced (수주 1~5건)": pick_diverse(bal, per_bucket, rng),
        "rich (수주 6건+)": pick_diverse(rich, per_bucket, rng),
    }


def format_amount(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v / 10_000:.0f}만"
    return f"{int(v):,}"


def _tokenize(s: str | None) -> set[str]:
    if not s:
        return set()
    import re
    # 공백/콤마/하이픈 토큰화
    return {t.strip() for t in re.split(r"[\s,·/\-]+", s) if t.strip() and len(t.strip()) >= 2}


def compute_metrics(company: dict, results: list[dict]) -> dict:
    """자동 메트릭 v2.

    - avg_score: 평균 최종 점수
    - industry_match_pct: 회사 등록업종/공급물품과 공고 참여가능업종에 공통 토큰 있는 추천 비율
    - instt_unique: TOP 5의 unique 기관 수 (단가계약 회사는 1이어도 정상)
    """
    if not results:
        return {"avg_score": 0, "industry_match_pct": 0, "instt_unique": 0}

    company_terms: set[str] = set()
    for nm in company.get("_industries", []) + company.get("_products", []):
        company_terms |= _tokenize(nm)

    matched = 0
    for r in results:
        notice_terms = _tokenize(r.get("bidprc_psbl_indstryty_nm")) | _tokenize(r.get("bid_ntce_nm"))
        if company_terms & notice_terms:
            matched += 1

    instt_counter = Counter(
        r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "—" for r in results
    )
    avg_score = sum(r.get("score", 0) for r in results) / len(results)
    return {
        "avg_score": round(avg_score, 3),
        "industry_match_pct": round(matched / len(results) * 100, 1),
        "instt_unique": len(instt_counter),
    }


def render_company_block(bucket: str, company: dict, result: dict) -> str:
    bizrno_norm = company["bizrno_norm"]
    rows = result.get("results") or []
    metrics = compute_metrics(company, rows)
    err = result.get("error")

    industries = company.get("_industries") or []
    products = company.get("_products") or []
    lines = [
        f"### [{bucket}] {company.get('corp_nm')} ({bizrno_norm})",
        "",
        f"- 업무구분: `{company.get('corp_bsns_div_nm') or '—'}` · "
        f"지역: {company.get('rgn_nm') or '—'} · "
        f"수주: {company.get('_suju', 0)}건",
        f"- 등록업종({len(industries)}): "
        f"{', '.join(industries[:6]) if industries else '—'}",
        f"- 공급물품({len(products)}): "
        f"{', '.join(products[:6]) if products else '—'}",
    ]
    if err:
        lines.append(f"- ⚠️ {err}")
        return "\n".join(lines) + "\n"

    lines.append(
        f"- 자동 메트릭: 평균 점수 **{metrics['avg_score']}** · "
        f"업종 토큰 매칭 **{metrics['industry_match_pct']}%** · "
        f"unique 기관 **{metrics['instt_unique']}/5**"
    )
    lines.append("")
    lines.append("| # | 공고명 | 기관 | 업무 | 추정가 | 점수 |")
    lines.append("| ---: | --- | --- | --- | ---: | ---: |")
    for i, r in enumerate(rows, 1):
        nm = (r.get("bid_ntce_nm") or "").replace("|", "\\|")
        if len(nm) > 50:
            nm = nm[:47] + "…"
        instt = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "—"
        if len(instt) > 20:
            instt = instt[:17] + "…"
        bsns = r.get("bsns_div_nm") or "—"
        price = format_amount(r.get("presmpt_prce") or r.get("asign_bdgt_amt"))
        score = round(r.get("score", 0), 3)
        sim = round(r.get("base_similarity", 0), 3)
        lines.append(
            f"| {i} | [{nm}](/notices/{r.get('bid_ntce_no')}) | {instt} | {bsns} | "
            f"{price} | {score} (sim {sim}) |"
        )
    lines.append("")
    return "\n".join(lines)


def render_report(samples_by_bucket: dict[str, list[dict]], all_results: dict[str, list[dict]]) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    total_companies = sum(len(v) for v in samples_by_bucket.values())

    # 전체 메트릭 집계
    all_metrics: list[dict] = []
    for bucket, samples in samples_by_bucket.items():
        for c in samples:
            result = all_results[c["bizrno_norm"]]
            if result.get("results"):
                all_metrics.append(compute_metrics(c, result["results"]))

    if all_metrics:
        avg_score = sum(m["avg_score"] for m in all_metrics) / len(all_metrics)
        avg_match = sum(m["industry_match_pct"] for m in all_metrics) / len(all_metrics)
        avg_uniq = sum(m["instt_unique"] for m in all_metrics) / len(all_metrics)
    else:
        avg_score = avg_match = avg_uniq = 0

    header = [
        f"# 추천 품질 정성 평가 v2 — {now}",
        "",
        f"- 평가 회사 수: **{total_companies}**개 (3개 버킷, 풍부화된 회사만)",
        f"- 전체 평균 매칭 점수: **{avg_score:.3f}**",
        f"- 전체 평균 업종 토큰 매칭: **{avg_match:.1f}%**",
        f"- 전체 평균 unique 기관 수: **{avg_uniq:.1f}/5**",
        "",
        "**검토 포인트**",
        "- 회사 정체성과 추천 공고가 직관적으로 맞나",
        "- 콜드스타트 버킷(수주 0건)에서 업종만으로 추천이 그럴듯한가",
        "- 풍부 버킷에서 과거 수주가 추천에 잘 반영됐나",
        "- 같은 기관이 너무 몰려 있지 않나 (다양성 < 3이면 의심)",
        "- 업무구분 일치율이 0% 가까운 회사가 있나 (있다면 왜)",
        "",
        "---",
        "",
    ]

    body = []
    for bucket, samples in samples_by_bucket.items():
        body.append(f"## {bucket}\n")
        for c in samples:
            body.append(render_company_block(bucket, c, all_results[c["bizrno_norm"]]))
        body.append("")

    return "\n".join(header + body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-bucket", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--bizrnos",
        nargs="+",
        default=None,
        help="평가할 bizrno_norm을 명시 지정 (sampling 무시). 이전 평가와 동일 회사로 비교할 때 사용.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    client = get_admin_client()
    print("[eval] fetching contract counts...")
    contract_counts = fetch_contract_counts(client)
    print(f"[eval] companies with contracts: {len(contract_counts):,}")

    print("[eval] fetching candidate companies (with embedding)...")
    pool = fetch_candidate_companies(client)
    print(f"[eval] candidate pool: {len(pool):,}")

    # 풍부화된 회사 (등록업종 있는 회사)만 통과
    print("[eval] fetching company industries to filter enriched-only...")
    industries_map = fetch_industries(client, [c["bizrno"] for c in pool])
    products_map = fetch_supply_products(client, [c["bizrno"] for c in pool])
    enriched_pool = []
    for c in pool:
        ind = industries_map.get(c["bizrno"], [])
        prd = products_map.get(c["bizrno"], [])
        if ind or prd:
            c["_industries"] = ind
            c["_products"] = prd
            enriched_pool.append(c)
    print(f"[eval] enriched pool: {len(enriched_pool):,} / {len(pool):,}")
    pool = enriched_pool

    if args.bizrnos:
        # 명시 지정 — 풀에서 해당 회사만 추리고 동일 버킷 분류
        wanted = set(args.bizrnos)
        explicit = [c for c in pool if c["bizrno_norm"] in wanted]
        missing = wanted - {c["bizrno_norm"] for c in explicit}
        if missing:
            print(f"[eval] pool miss {len(missing)} bizrnos -> direct fetch")
            extra = (
                client.table("companies")
                .select("bizrno,bizrno_norm,corp_nm,corp_bsns_div_nm,mnfctr_div_nm,rgn_nm,is_restricted")
                .in_("bizrno_norm", list(missing))
                .execute()
                .data
            ) or []
            # 누락 회사의 industries/products도 별도 fetch해서 map 갱신
            missing_bizrnos = [c["bizrno"] for c in extra]
            if missing_bizrnos:
                industries_map.update(fetch_industries(client, missing_bizrnos))
                products_map.update(fetch_supply_products(client, missing_bizrnos))
            for c in extra:
                if c.get("is_restricted"):
                    continue
                c["_industries"] = industries_map.get(c["bizrno"], [])
                c["_products"] = products_map.get(c["bizrno"], [])
                explicit.append(c)
        # 버킷 분류 (수주 수 기준)
        samples_by_bucket = {
            "cold (수주 0건, 업종 100%)": [],
            "balanced (수주 1~5건)": [],
            "rich (수주 6건+)": [],
        }
        for c in explicit:
            cnt = contract_counts.get(c["bizrno_norm"], 0)
            c["_suju"] = cnt
            if cnt == 0:
                samples_by_bucket["cold (수주 0건, 업종 100%)"].append(c)
            elif cnt <= 5:
                samples_by_bucket["balanced (수주 1~5건)"].append(c)
            else:
                samples_by_bucket["rich (수주 6건+)"].append(c)
    else:
        samples_by_bucket = sample_by_bucket(pool, contract_counts, args.per_bucket, rng)
    for bucket, samples in samples_by_bucket.items():
        print(f"  {bucket}: {len(samples)}개")

    all_results: dict[str, list[dict]] = {}
    for bucket, samples in samples_by_bucket.items():
        for c in samples:
            print(f"[eval] recommending {c['corp_nm']} ({c['bizrno_norm']})...")
            try:
                result = recommend(c["bizrno_norm"], limit=5, candidate_pool=200)
            except Exception as e:
                result = {"error": f"추천 실패: {type(e).__name__}: {e}", "results": []}
            all_results[c["bizrno_norm"]] = result

    md = render_report(samples_by_bucket, all_results)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / f"eval-{ts}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[eval] wrote {out}")
    print(f"[eval] open this file in your editor to review.")


if __name__ == "__main__":
    main()
