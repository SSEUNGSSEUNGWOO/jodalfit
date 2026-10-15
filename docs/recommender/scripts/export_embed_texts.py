"""임베딩 모델 실험용 텍스트 추출: 시점 t 의 활성 공고 + 표본 회사의 이력 공고 + 표본 회사의 업종 텍스트.
출력: JSON {"notices": {"no|ord": text}, "texts": [industry text...]}  (운영 embed_bid_notices.build_text 와 동일 텍스트)
사용: PYTHONPATH=. uv run python export_embed_texts.py 2026-08-01 out.json
"""
import json, sys
from datetime import date, timedelta
sys.stdout.reconfigure(encoding="utf-8")
from jobs.evaluate_recommender import (connect, fetch_positives, sample_companies, fetch_company_profile, fetch_history_before,
                                       strip_leaked_history, HORIZON_DAYS)
from jobs.embed_bid_notices import build_text
from jobs.compute_company_vectors import build_industry_text

t = date.fromisoformat(sys.argv[1]); out = sys.argv[2]
horizon = t + timedelta(days=HORIZON_DAYS)
conn = connect()
positives = fetch_positives(conn, t, horizon, "winner")
sample = sample_companies(conn, positives, t, 300, 7)
keys: set[tuple[str, str]] = set()
texts: set[str] = set()
for s in sample:
    prof = fetch_company_profile(conn, s["biz"])
    txt = build_industry_text({}, prof["industries"], prof["products"])
    if txt:
        texts.add(txt)
    hist, _, _ = fetch_history_before(conn, s["biz"], t)
    hist = strip_leaked_history(hist, positives[s["biz"]])
    keys |= {(h["bid_ntce_no"], h["bid_ntce_ord"]) for h in hist}
print(f"sample {len(sample)} companies · industry texts {len(texts)} · history keys {len(keys):,}")
notices: dict[str, str] = {}
cols = "bid_ntce_no, bid_ntce_ord, bid_ntce_nm, bsns_div_nm, bidprc_psbl_indstryty_nm, dmnd_instt_nm, raw"
for no, od, nm, div, ind, dm, raw in conn.execute(
    f"select {cols} from bid_notices where embedding is not null and bid_ntce_date < %s and bid_clse_date >= %s and bid_clse_date <= %s", (t, t, horizon)):
    notices[f"{no}|{od}"] = build_text({"bid_ntce_nm": nm, "bsns_div_nm": div, "bidprc_psbl_indstryty_nm": ind, "dmnd_instt_nm": dm, "raw": raw})
n_active = len(notices)
if keys:
    for no, od, nm, div, ind, dm, raw in conn.execute(
        f"select {cols} from bid_notices where (bid_ntce_no, bid_ntce_ord) in (select unnest(%s::text[]), unnest(%s::text[])) and embedding is not null",
        ([k[0] for k in keys], [k[1] for k in keys])):
        notices.setdefault(f"{no}|{od}", build_text({"bid_ntce_nm": nm, "bsns_div_nm": div, "bidprc_psbl_indstryty_nm": ind, "dmnd_instt_nm": dm, "raw": raw}))
print(f"active notices {n_active:,} · total notice texts {len(notices):,}")
json.dump({"as_of": t.isoformat(), "notices": notices, "texts": sorted(texts)}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print("written", out)
