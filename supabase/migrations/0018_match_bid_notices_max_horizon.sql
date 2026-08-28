-- 추천 후보에서 장기 단가계약성 공고 제외.
--
-- 문제: 필터가 `bid_clse_date >= today` 하한뿐이라 상한이 없다. 마감이 수년 뒤인
-- 조달청 종합쇼핑몰 단가계약 품목(흙콘크리트·전선관·화장지 등)이 이 필터를 영구히
-- 통과해 모든 회사의 후보 풀에 남는다. 실측 결과 만평산업은 RPC top-200 중 169건,
-- 삼성에스디에스는 TOP 20 중 12건이 이런 공고였다.
--
-- 활성 공고의 마감 분포는 D+60 이후 절벽이다(D+30~60 209건 → D+60~90 5건).
-- max_clse_date로 상한을 걸어 호출자가 지평선을 정하게 한다. null이면 종전과 동일.
--
-- create or replace가 아니라 drop 후 create인 이유: 파라미터를 추가하면 arity가
-- 달라져 새 overload가 생기고, 인자 4개 이하 호출이 두 함수 사이에서 모호해져
-- PGRST203으로 깨진다(0011에서 match_pre_specs가 겪은 문제와 동일).

begin;

drop function if exists match_bid_notices(vector, int, date, text);

create function match_bid_notices(
  query_embedding vector(1536),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null,
  max_clse_date date default null
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

commit;
