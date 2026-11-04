"""임베딩 모델·텍스트 변형 실험용 텍스트 추출 (2026-11-04, export_embed_texts.py 의 확장).

시점 t 의 활성 공고 + 표본 회사의 이력 공고 + 표본 회사의 업종 텍스트를 JSON 으로. 하네스 --embeddings 와 짝.
한 번 실행에 네 변형을 전부 쓴다(회사 조회가 비용의 대부분이라) — <out_prefix>-<variant>-<date>.json
출력: {"as_of", "variant", "notices": {"no|ord": text}, "texts": [industry text...]}

사용: cd backend && PYTHONPATH=. uv run python ../docs/recommender/scripts/export_embed_texts2.py 2026-08-01 data/emb_rematch/texts --n 3000
variant:
  base    운영 embed_bid_notices.build_text 그대로(공고명·업무구분·참가가능업종·품목분류·규격·주공종·용역구분·수요기관)
  insight base + 첨부문서 인사이트(summary·scope) — 있는 공고만
  noinst  base 에서 수요기관 줄 제거
  plain   항목 이름 없이 값만 ", " 로 이어 붙임
활성 공고 집합은 `embedding is not null`(OpenAI 열, 2026-10 이전 전수) — 하네스는 --space openai 로 같은 집합을 본다.
회사 프로필은 하네스와 같이 시점 t 로 복원한다(fetch_company_profile(conn, biz, t)) — 아니면 업종 텍스트가 달라 하네스가 멈춘다.
"""
import argparse, json, sys
from datetime import date, timedelta
sys.stdout.reconfigure(encoding="utf-8")
from jobs.evaluate_recommender import (connect, fetch_positives, sample_companies, fetch_company_profile, fetch_history_before,
                                       strip_leaked_history, HORIZON_DAYS)
from jobs.embed_bid_notices import build_text
from jobs.compute_company_vectors import build_industry_text

VARIANTS = ("base", "insight", "noinst", "plain")
ap = argparse.ArgumentParser()
ap.add_argument("as_of"); ap.add_argument("out_prefix")
ap.add_argument("--n", type=int, default=3000); ap.add_argument("--seed", type=int, default=7)
args = ap.parse_args()

t = date.fromisoformat(args.as_of); horizon = t + timedelta(days=HORIZON_DAYS)
conn = connect()
positives = fetch_positives(conn, t, horizon, "winner")
sample = sample_companies(conn, positives, t, args.n, args.seed)
keys: set[tuple[str, str]] = set(); texts: set[str] = set()
for i, s in enumerate(sample):
    prof = fetch_company_profile(conn, s["biz"], t)
    txt = build_industry_text({}, prof["industries"], prof["products"])
    if txt: texts.add(txt)
    hist, _, _ = fetch_history_before(conn, s["biz"], t)
    hist = strip_leaked_history(hist, positives[s["biz"]])
    keys |= {(h["bid_ntce_no"], h["bid_ntce_ord"]) for h in hist}
    if (i + 1) % 500 == 0: print(f"  companies {i + 1}/{len(sample)} · history keys {len(keys):,}", flush=True)
print(f"sample {len(sample)} companies · industry texts {len(texts)} · history keys {len(keys):,}", flush=True)


def texts_of(nm, div, ind, dm, raw, summary, scope) -> dict[str, str]:
    base = build_text({"bid_ntce_nm": nm, "bsns_div_nm": div, "bidprc_psbl_indstryty_nm": ind, "dmnd_instt_nm": dm, "raw": raw})
    noinst = build_text({"bid_ntce_nm": nm, "bsns_div_nm": div, "bidprc_psbl_indstryty_nm": ind, "dmnd_instt_nm": None, "raw": raw})
    def s(v) -> str:  # insights 의 scope 는 jsonb 배열, summary 는 문자열
        return ", ".join(str(x).strip() for x in v if str(x).strip()) if isinstance(v, list) else (v or "").strip()
    extra = [f"요약: {s(summary)}"] if s(summary) else []
    extra += [f"범위: {s(scope)}"] if s(scope) else []
    return {
        "base": base,
        "insight": "\n".join([base, *extra]),
        "noinst": noinst,
        "plain": ", ".join(line.split(": ", 1)[1] if ": " in line else line for line in base.split("\n")),
    }


cols = "b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm, b.bidprc_psbl_indstryty_nm, b.dmnd_instt_nm, b.raw, i.summary, i.scope"
join = "left join bid_notice_insights i using (bid_ntce_no, bid_ntce_ord)"
notices: dict[str, dict[str, str]] = {}; n_ins = 0
for no, od, nm, div, ind, dm, raw, summ, scope in conn.execute(
        f"select {cols} from bid_notices b {join} where b.embedding is not null and b.bid_ntce_date < %s and b.bid_clse_date >= %s and b.bid_clse_date <= %s",
        (t, t, horizon)):
    notices[f"{no}|{od}"] = texts_of(nm, div, ind, dm, raw, summ, scope); n_ins += bool(summ)
n_active = len(notices)
if keys:
    for no, od, nm, div, ind, dm, raw, summ, scope in conn.execute(
            f"select {cols} from bid_notices b {join} where (b.bid_ntce_no, b.bid_ntce_ord) in (select unnest(%s::text[]), unnest(%s::text[])) and b.embedding is not null",
            ([k[0] for k in keys], [k[1] for k in keys])):
        notices.setdefault(f"{no}|{od}", texts_of(nm, div, ind, dm, raw, summ, scope))
print(f"active notices {n_active:,} (insight {n_ins:,}) · total notice texts {len(notices):,}", flush=True)
for v in VARIANTS:
    out = f"{args.out_prefix}-{v}-{t.isoformat()}.json"
    json.dump({"as_of": t.isoformat(), "variant": v, "notices": {k: d[v] for k, d in notices.items()}, "texts": sorted(texts)},
              open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("written", out, flush=True)
