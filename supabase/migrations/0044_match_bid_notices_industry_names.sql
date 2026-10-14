-- 후보 검색 업종 채널.
--
-- 평가 하네스 결과(docs/recommender/exp-2026-10-14-retrieval.md): dense 검색이 놓친 낙찰 공고의
-- 56%는 회사 등록업종이 공고 허용업종(bidprc_psbl_indstryty_nm)에 들어 있는 공고였다.
-- industry_names 가 주어지면 그 업종을 허용하는 공고 안에서만 유사도 검색한다. null 이면 종전과 동일.
-- 호출 측(recommend.py)이 dense 호출과 업종 호출을 병렬로 보내 번갈아 합친다.
--
-- 0018 과 같은 이유로 create or replace 가 아니라 drop 후 create (arity 가 달라지면 overload 모호 → PGRST203).
-- 활성 공고 CTE 는 ~1만 행 정확 탐색이라 필터가 늘어도 비용은 같거나 줄어든다(실측 230ms → 187ms).

begin;

drop function if exists match_bid_notices(vector, int, date, text, date);

create function match_bid_notices(
  query_embedding vector(1536),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null,
  max_clse_date date default null,
  industry_names text[] default null
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
      and (max_clse_date is null or b.bid_clse_date <= max_clse_date)
      and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
      and (industry_names is null
           or exists (select 1 from unnest(industry_names) n
                      where b.bidprc_psbl_indstryty_nm like '%' || n || '%'))
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

notify pgrst, 'reload schema';

commit;
