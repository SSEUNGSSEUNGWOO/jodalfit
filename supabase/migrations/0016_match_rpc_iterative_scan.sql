-- match_bid_notices statement timeout(57014) 해결.
--
-- 원인: `where bid_clse_date >= today`를 통과하는 공고는 전체의 ~3%(약 1만 건)뿐인데,
-- 함수 내부 플랜이 HNSW 인덱스를 걷으며 97%를 버리는 경로를 타면 수 초~타임아웃.
-- 반대로 날짜 btree로 먼저 거른 뒤 1만 건을 정확 정렬하면 ~100ms (EXPLAIN 실측).
--
-- 해결: materialized CTE로 "필터 먼저 → 정확 top-N 정렬" 플랜을 강제.
-- min_clse_date는 null이면 current_date로 보정 — 전 호출자가 활성 공고만 원하며,
-- null로 전체 30만 건을 materialize하는 사고를 방지.

create or replace function match_bid_notices(
  query_embedding vector(1536),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null
)
returns table (
  bid_ntce_no text,
  bid_ntce_ord text,
  bid_ntce_nm text,
  bsns_div_nm text,
  bid_ntce_date date,
  bid_clse_date date,
  openg_date date,
  presmpt_prce bigint,
  ntce_instt_nm text,
  dmnd_instt_nm text,
  bidprc_psbl_indstryty_nm text,
  rgn_lmt_yn char(1),
  prtcpt_psbl_rgn_nm text,
  indstryty_lmt_yn char(1),
  bid_ntce_url text,
  similarity real
)
language sql
stable
as $$
  with active as materialized (
    select b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
           b.bid_ntce_date, b.bid_clse_date, b.openg_date,
           b.presmpt_prce, b.ntce_instt_nm, b.dmnd_instt_nm,
           b.bidprc_psbl_indstryty_nm, b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm,
           b.indstryty_lmt_yn, b.bid_ntce_url, b.embedding
    from bid_notices b
    where b.embedding is not null
      and b.bid_clse_date >= coalesce(min_clse_date, current_date)
      and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
  )
  select a.bid_ntce_no, a.bid_ntce_ord, a.bid_ntce_nm, a.bsns_div_nm,
         a.bid_ntce_date, a.bid_clse_date, a.openg_date,
         a.presmpt_prce, a.ntce_instt_nm, a.dmnd_instt_nm,
         a.bidprc_psbl_indstryty_nm, a.rgn_lmt_yn, a.prtcpt_psbl_rgn_nm,
         a.indstryty_lmt_yn, a.bid_ntce_url,
         (1 - (a.embedding <=> query_embedding))::real as similarity
  from active a
  order by a.embedding <=> query_embedding
  limit match_count;
$$;
