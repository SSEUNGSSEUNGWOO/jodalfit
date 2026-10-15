"""KURE-v1 백필 (노트북 GPU, torch env) — embedding_k 를 채운다. 0045 적용 뒤 실행.
대상: 공고(마감 90일 이내 + 회사 이력 공고 전부), 진행 중 사전규격·발주계획.
회사 업종 텍스트 캐시(text_embeddings)는 여기서 채우지 않는다 — compute_company_vectors --space kure
를(KURE_BACKEND=torch) 돌리면 그 잡이 쓰는 키(sha1)가 production 과 그대로 일치하므로, 공고 백필 뒤
그 잡 실행만으로 캐시가 채워진다.
사용: cd backend && PYTHONPATH=. C:\dev\ops\jodalfit\design\.venv\Scripts\python.exe ../docs/recommender/scripts/backfill_kure.py [--what notices,prespecs,plans] [--batch 64]
"""
import argparse, sys, time
import numpy as np, psycopg, torch
from sentence_transformers import SentenceTransformer
from dotenv import dotenv_values
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from jobs.embed_bid_notices import build_text

URL = dotenv_values(".env")["DATABASE_URL"]
ap = argparse.ArgumentParser(); ap.add_argument("--what", default="notices,prespecs,plans"); ap.add_argument("--batch", type=int, default=64); ap.add_argument("--limit", type=int, default=0)
args = ap.parse_args(); what = set(args.what.split(","))
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = SentenceTransformer("nlpai-lab/KURE-v1", device=dev); m.half() if dev == "cuda" else None; m.max_seq_length = 512
print("device", dev)


def enc(texts):
    return m.encode(texts, batch_size=args.batch, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)


def vec(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


conn = psycopg.connect(URL, connect_timeout=20, autocommit=True)
conn.execute("set statement_timeout = 600000")

if "notices" in what:
    cols = "bid_ntce_no, bid_ntce_ord, bid_ntce_nm, bsns_div_nm, bidprc_psbl_indstryty_nm, dmnd_instt_nm, raw"
    q = f"""select {cols} from bid_notices b where b.embedding_k is null and b.embedding is not null and (
              b.bid_clse_date >= current_date - 90
              or exists (select 1 from contracts c where c.bid_ntce_no = b.bid_ntce_no and c.bid_ntce_ord = b.bid_ntce_ord)
              or exists (select 1 from award_results a where a.bid_ntce_no = b.bid_ntce_no and a.bid_ntce_ord = b.bid_ntce_ord and a.bizrno_norm <> ''))
            order by b.bid_clse_date desc""" + (f" limit {args.limit}" if args.limit else "")
    t0 = time.time(); done = 0; chunk = []

    def flush(chunk):
        texts = [build_text({"bid_ntce_nm": r[2], "bsns_div_nm": r[3], "bidprc_psbl_indstryty_nm": r[4], "dmnd_instt_nm": r[5], "raw": r[6]}) for r in chunk]
        E = enc(texts)
        with conn.cursor() as cur:
            cur.executemany("update bid_notices set embedding_k = %s::vector, embedded_k_at = now() where bid_ntce_no = %s and bid_ntce_ord = %s", [(vec(E[k]), r[0], r[1]) for k, r in enumerate(chunk)])
        return len(chunk)

    with conn.cursor(name="bf", withhold=True) as scur:
        scur.itersize = 1000
        scur.execute(q)
        for r in scur:
            chunk.append(r)
            if len(chunk) >= 1000:
                done += flush(chunk); print(f"  {done:,}  {time.time() - t0:.0f}s"); chunk = []
        if chunk:
            done += flush(chunk); print(f"  {done:,}  {time.time() - t0:.0f}s")
    print(f"notices embedded: {done:,}")

if "prespecs" in what or "plans" in what:
    from jobs.embed_pre_specs import build_text as pre_text  # noqa
    from jobs.embed_order_plans import build_text as plan_text  # noqa
    for name, table, key, builder in (("prespecs", "pre_specs", "bf_spec_rgst_no", pre_text), ("plans", "order_plans", "order_plan_unty_no", plan_text)):
        if name not in what: continue
        rows = conn.execute(f"select * from {table} where embedding_k is null and embedding is not null" + (f" limit {args.limit}" if args.limit else "")).fetchall()
        cols = [d.name for d in conn.execute(f"select * from {table} limit 0").description]
        print(f"{table} to embed: {len(rows):,}")
        for i in range(0, len(rows), 1000):
            chunk = [dict(zip(cols, r)) for r in rows[i:i + 1000]]; E = enc([builder(r) for r in chunk])
            with conn.cursor() as cur:
                cur.executemany(f"update {table} set embedding_k = %s::vector where {key} = %s", [(vec(E[k]), r[key]) for k, r in enumerate(chunk)])
            print(f"  {min(i + 1000, len(rows)):,}/{len(rows):,}")
print("backfill done")
