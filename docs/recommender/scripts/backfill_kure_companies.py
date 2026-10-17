"""KURE 회사 벡터 백필 (GPU, DATABASE_URL 직접 접속) — embedding_k 가 없는 회사만 채운다.

compute_company_vectors --space kure 는 모든 읽기를 PostgREST 로 하느라 100곳 청크에 7분이
걸렸다(2026-10-15, 분당 12곳). 같은 재료·같은 수식(dynamic_weights·시간가중·CLS+L2)을
psycopg 로 직접 읽고 쓴다. 공고 벡터는 청크 간 메모리 캐시, 업종 텍스트는 0046 text_embeddings
캐시(sha1 키가 잡과 동일)를 그대로 공유하므로 production 결과와 같은 벡터가 나온다.

대상: companies.embedding(OpenAI) 은 있는데 embedding_k 가 없는 회사. 끝난 회사는 다음 실행에서
빠지므로 끊겨도 다시 돌리면 이어서 한다.

사용: cd backend && uv run --no-sync python ../docs/recommender/scripts/backfill_kure_companies.py [--limit N] [--chunk 200]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime

import numpy as np
import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())  # backend/ 에서 실행 — jobs.*, app.* import
load_dotenv(".env")  # DATABASE_URL + KURE_BACKEND=torch (local_embed 는 os.environ 만 본다)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.embedding import _cached, _sha1  # noqa: E402
from app.services.local_embed import _torch  # noqa: E402
from app.services.openai_client import vector_to_pgvector_str  # noqa: E402
from jobs._common import log_ingest_finish, log_ingest_start  # noqa: E402
from jobs.compute_company_vectors import (  # noqa: E402
    build_industry_text,
    chunks,
    dynamic_weights,
    normalize,
    parse_pgvector,
)

HALF_LIFE = 365.0
PARTICIPATION_WEIGHT = 0.4
SPACE = "kure"


def time_weight(ds, today: date) -> float:
    if not ds:
        return 1.0
    try:
        d = date.fromisoformat(str(ds)[:10])
        return 0.5 ** (max((today - d).days, 0) / HALF_LIFE)
    except Exception:
        return 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = 전부")
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--batch", type=int, default=64, help="GPU encode batch")
    args = ap.parse_args()

    model = _torch()
    print(f"device={model.device} backend={os.environ.get('KURE_BACKEND')}")

    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=20, autocommit=True)
    conn.execute("set statement_timeout = 600000")

    def encode(texts: list[str]) -> list[list[float]]:
        cleaned = [t.strip() or "(empty)" for t in texts]  # local_embed.embed_texts_kure 와 동일 관례
        return model.encode(
            cleaned, batch_size=args.batch, normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32).tolist()

    def cache_lookup(shas: list[str]) -> dict[str, list[float]]:
        rows = conn.execute(
            "select text_sha1, embedding::text from text_embeddings where space = %s and text_sha1 = any(%s)",
            (SPACE, shas),
        ).fetchall()
        return {s: parse_pgvector(e).tolist() for s, e in rows}

    def cache_store(fresh: dict[str, list[float]]) -> None:
        with conn.cursor() as cur:
            cur.executemany(
                "insert into text_embeddings (space, text_sha1, embedding) values (%s, %s, %s::vector) "
                "on conflict (space, text_sha1) do update set embedding = excluded.embedding",
                [(SPACE, s, vector_to_pgvector_str(e)) for s, e in fresh.items()],
            )

    targets = [
        r[0]
        for r in conn.execute(
            "select bizrno_norm from companies where embedding is not null and embedding_k is null "
            "and bizrno_norm is not null group by 1 order by 1"
        ).fetchall()
    ]
    if args.limit:
        targets = targets[: args.limit]
    print(f"targets={len(targets):,} chunk={args.chunk}")
    run_id = log_ingest_start(
        "compute_company_vectors",
        {"space": SPACE, "mode": "direct-gpu-backfill", "limit": args.limit, "chunk": args.chunk},
    )

    notice_vecs: dict[tuple[str, str], np.ndarray] = {}
    today = date.today()
    total = skipped = 0
    t0 = time.time()
    try:
        for ci, ch in enumerate(chunks(targets, args.chunk), 1):
            corps = conn.execute(
                "select bizrno, bizrno_norm from companies where bizrno_norm = any(%s)", (ch,)
            ).fetchall()
            norm_to_rows: dict[str, list[str]] = defaultdict(list)
            for bizrno, norm in corps:
                norm_to_rows[norm].append(bizrno)
            biz_to_norm = {b: n for n, rows in norm_to_rows.items() for b in rows}
            biz_pks = list(biz_to_norm)

            ind: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
            for bizrno, nm, rep_yn in conn.execute(
                "select bizrno, indstryty_nm, rprsnt_indstryty_yn from company_industries where bizrno = any(%s)",
                (biz_pks,),
            ):
                if not nm:
                    continue
                rep, rest = ind[biz_to_norm[bizrno]]
                if nm in rep or nm in rest:
                    continue
                (rep if rep_yn == "Y" else rest).append(nm)
            sup: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
            for bizrno, nm, rep_yn in conn.execute(
                "select bizrno, dtl_prdct_clsfc_nm, rprsnt_prdct_yn from company_supply_products where bizrno = any(%s)",
                (biz_pks,),
            ):
                if not nm:
                    continue
                rep, rest = sup[biz_to_norm[bizrno]]
                if nm in rep or nm in rest:
                    continue
                (rep if rep_yn == "Y" else rest).append(nm)

            contracts = conn.execute(
                "select rprsnt_corp_bizrno_norm, bid_ntce_no, bid_ntce_ord, cntrct_cncls_date "
                "from contracts where rprsnt_corp_bizrno_norm = any(%s)",
                (ch,),
            ).fetchall()
            parts = conn.execute(
                "select bizrno, bid_ntce_no, bid_ntce_ord, created_at, raw->>'bidprcDt' "
                "from award_results where bizrno = any(%s) and is_winner = false",
                (ch,),
            ).fetchall()

            need = {(r[1], r[2]) for r in contracts + parts if r[1]} - notice_vecs.keys()
            if need:
                for no, ord_, emb in conn.execute(
                    "select bid_ntce_no, bid_ntce_ord, embedding_k::text from bid_notices "
                    "where bid_ntce_no = any(%s) and embedding_k is not null",
                    (sorted({k[0] for k in need}),),
                ):
                    v = parse_pgvector(emb)
                    if v is not None:
                        notice_vecs[(no, ord_)] = v

            suju: dict[str, list[tuple[float, np.ndarray]]] = defaultdict(list)
            suju_count: dict[str, float] = defaultdict(float)
            for b, no, ord_, d in contracts:
                suju_count[b] += 1
                v = notice_vecs.get((no, ord_))
                if v is not None:
                    suju[b].append((time_weight(d, today), v))
            for b, no, ord_, created, bidprc in parts:
                suju_count[b] += PARTICIPATION_WEIGHT
                v = notice_vecs.get((no, ord_))
                if v is not None:
                    suju[b].append((time_weight(bidprc or created, today) * PARTICIPATION_WEIGHT, v))
            suju_vec: dict[str, np.ndarray] = {}
            for b, pairs in suju.items():
                ws = np.array([p[0] for p in pairs], dtype=np.float32)
                if ws.sum() == 0:
                    continue
                suju_vec[b] = (np.stack([p[1] for p in pairs]) * ws[:, None]).sum(axis=0) / ws.sum()

            texts, text_targets = [], []
            for b in ch:
                if b not in norm_to_rows:
                    continue
                t = build_industry_text({}, ind.get(b, ([], [])), sup.get(b, ([], [])))
                if t:
                    texts.append(t)
                    text_targets.append(b)
            ind_vec: dict[str, np.ndarray] = {}
            if texts:
                for b, e in zip(text_targets, _cached(texts, cache_lookup, cache_store, encode)):
                    ind_vec[b] = np.array(e, dtype=np.float32)

            now_iso = datetime.now().isoformat()
            updates: list[tuple[str, str, str]] = []
            for b in ch:
                if b not in norm_to_rows:
                    skipped += 1
                    continue
                w = dynamic_weights(suju_count.get(b, 0), False)
                signals = []
                if b in ind_vec:
                    signals.append((w["industry"], ind_vec[b]))
                if b in suju_vec:
                    signals.append((w["suju"], suju_vec[b]))
                tw = sum(s[0] for s in signals)
                if not signals or tw == 0:
                    skipped += 1
                    continue
                out = np.zeros_like(signals[0][1])
                for wt, v in signals:
                    out += (wt / tw) * v
                vs = vector_to_pgvector_str(normalize(out).tolist())
                updates.extend((vs, now_iso, bizrno) for bizrno in norm_to_rows[b])
            if updates:
                with conn.cursor() as cur:
                    cur.executemany(
                        "update companies set embedding_k = %s::vector, embedded_k_at = %s where bizrno = %s",
                        updates,
                    )
            total += len(updates)
            if ci % 5 == 0 or ci * args.chunk >= len(targets):
                el = time.time() - t0
                done = min(ci * args.chunk, len(targets))
                print(
                    f"  [{done:,}/{len(targets):,}] vectors {total:,} | skipped {skipped:,} | "
                    f"{done / el * 60:,.0f}/min | notice cache {len(notice_vecs):,}",
                    flush=True,
                )
        log_ingest_finish(run_id, "success", rows_updated=total)
        print(f"done. {total:,} vectors / {skipped:,} skipped / {time.time() - t0:.0f}s")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_updated=total, error_msg=str(e))
        raise


if __name__ == "__main__":
    main()
