"""물품 통로를 만들 가치가 있나 — 놓친 낙찰 공고 중 '공고 물품분류번호 ∩ 회사 공급물품 코드' 가 비어 있지 않은 비율.
업종 통로(0044)는 같은 질문에 56% 가 나와서 만들었다. 실행: uv run python -m jobs.probe_prdct_channel <run_dir> ..."""

import csv
import io
import os
import sys
from collections import Counter

import psycopg
from dotenv import load_dotenv

load_dotenv()

SQL_N = "select bid_ntce_no, bsns_div_nm, prdct_clsfc_nos from bid_notices where bid_ntce_no = any(%s)"
SQL_C = "select replace(bizrno,'-',''), array_agg(distinct dtl_prdct_clsfc_no) from company_supply_products where replace(bizrno,'-','') = any(%s) group by 1"


def probe(conn, run):
    fails = list(csv.DictReader(io.open(f"{run}/failures.csv", encoding="utf-8")))
    nos = sorted({f["bid_ntce_no"] for f in fails})
    bizs = sorted({f["biz"] for f in fails})
    notice = {no: (div, set(codes or [])) for no, div, codes in conn.execute(SQL_N, (nos,))}
    comp = {b: set(c) for b, c in conn.execute(SQL_C, (bizs,))}
    tot, hit, by_stage, by_stage_hit = Counter(), Counter(), Counter(), Counter()
    no_code, no_comp = 0, 0
    for f in fails:
        div, codes = notice.get(f["bid_ntce_no"], ("?", set()))
        if div != "물품":
            continue
        tot[div] += 1
        by_stage[f["lost_at"]] += 1
        if not codes:
            no_code += 1
        if f["biz"] not in comp:
            no_comp += 1
        if codes & comp.get(f["biz"], set()):
            hit[div] += 1
            by_stage_hit[f["lost_at"]] += 1
    n = tot["물품"]
    name = run.rstrip("/\\").split("/")[-1].split("\\")[-1]
    print(f"\n{name}: 놓친 공고 {len(fails)} 중 물품 {n}")
    if not n:
        return
    print(f"  코드 겹침 {hit['물품']} / {n} = {hit['물품'] / n * 100:.0f}%   (공고에 코드 없음 {no_code}, 회사에 공급물품 없음 {no_comp})")
    for st in ("dense", "dedup", "qualified", "scored"):
        if by_stage[st]:
            print(f"    {st:9} {by_stage_hit[st]:3} / {by_stage[st]:3}")


if __name__ == "__main__":
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for run in sys.argv[1:]:
            probe(conn, run)
