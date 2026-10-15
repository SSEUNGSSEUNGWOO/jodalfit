-- 후보 검색 물품 채널 — 업종 채널(0044)과 같은 구조.
--
-- 놓친 물품 낙찰 공고 중 '공고 물품분류번호(0047 prdct_clsfc_nos) ∩ 회사 공급물품 코드' 가 비어 있지 않은 비율이
-- 8/1 55%(공급물품 등록된 회사만 82%), 7/1 43% — 업종 채널의 근거였던 56% 와 같은 수준(jobs/probe_prdct_channel.py).
-- product_codes 가 주어지면 그 코드를 하나라도 가진 공고 안에서만 유사도 검색한다. null 이면 종전과 동일.
-- 호출 측(recommend.py)이 dense·업종·물품 세 채널을 병렬로 보내 번갈아 합친다.
--
-- 0044 와 같은 이유로 drop 후 create (arity 가 달라지면 PGRST203 overload 모호). GIN(bid_notices_prdct_clsfc_nos_gin) 사용.

begin;

drop function if exists match_bid_notices(vector, int, date, text, date, text[]);
drop function if exists match_bid_notices(vector, int, date, text, date, text[], text[]);

create function match_bid_notices(
  query_embedding vector(1536),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null,
  max_clse_date date default null,
  industry_names text[] default null,
  product_codes text[] default null
)
returns table (
  bid_ntce_no text, bid_ntce_ord text, bid_ntce_nm text, bsns_div_nm text,
  bid_ntce_date date, bid_clse_date date, openg_date date, presmpt_prce bigint,
  ntce_instt_nm text, dmnd_instt_nm text, bidprc_psbl_indstryty_nm text,
  rgn_lmt_yn char(1), prtcpt_psbl_rgn_nm text, indstryty_lmt_yn char(1), bid_ntce_url text,
  similarity real
)
language sql stable as $$
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
                      where position(n in b.bidprc_psbl_indstryty_nm) > 0))
      and (product_codes is null or b.prdct_clsfc_nos && product_codes)
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

drop function if exists match_bid_notices_k(vector, int, date, text, date, text[]);
drop function if exists match_bid_notices_k(vector, int, date, text, date, text[], text[]);

create function match_bid_notices_k(
  query_embedding vector(1024),
  match_count int default 50,
  min_clse_date date default null,
  bsns_div_filter text default null,
  max_clse_date date default null,
  industry_names text[] default null,
  product_codes text[] default null
)
returns table (
  bid_ntce_no text, bid_ntce_ord text, bid_ntce_nm text, bsns_div_nm text,
  bid_ntce_date date, bid_clse_date date, openg_date date, presmpt_prce bigint,
  ntce_instt_nm text, dmnd_instt_nm text, bidprc_psbl_indstryty_nm text,
  rgn_lmt_yn char(1), prtcpt_psbl_rgn_nm text, indstryty_lmt_yn char(1), bid_ntce_url text,
  similarity real
)
language sql stable as $$
  with active as materialized (
    select b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
           b.bid_ntce_date, b.bid_clse_date, b.openg_date,
           b.presmpt_prce, b.ntce_instt_nm, b.dmnd_instt_nm,
           b.bidprc_psbl_indstryty_nm, b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm,
           b.indstryty_lmt_yn, b.bid_ntce_url, b.embedding_k
    from bid_notices b
    where b.embedding_k is not null
      and b.bid_clse_date >= coalesce(min_clse_date, current_date)
      and (max_clse_date is null or b.bid_clse_date <= max_clse_date)
      and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
      and (industry_names is null
           or exists (select 1 from unnest(industry_names) n
                      where position(n in b.bidprc_psbl_indstryty_nm) > 0))
      and (product_codes is null or b.prdct_clsfc_nos && product_codes)
  )
  select a.bid_ntce_no, a.bid_ntce_ord, a.bid_ntce_nm, a.bsns_div_nm,
         a.bid_ntce_date, a.bid_clse_date, a.openg_date,
         a.presmpt_prce, a.ntce_instt_nm, a.dmnd_instt_nm,
         a.bidprc_psbl_indstryty_nm, a.rgn_lmt_yn, a.prtcpt_psbl_rgn_nm,
         a.indstryty_lmt_yn, a.bid_ntce_url,
         (1 - (a.embedding_k <=> query_embedding))::real as similarity
  from active a
  order by a.embedding_k <=> query_embedding
  limit match_count;
$$;

notify pgrst, 'reload schema';

commit;
