-- 입찰참가자격 등록 마감(bid_qlfct_rgst_dt, 0047)이 지난 공고를 후보에서 제외.
--
-- 이 시각은 입찰 마감보다 먼저 닫히는 진짜 데드라인이다 — 지나면 아무리 맞는 공고여도 낼 수 없다.
-- 2026-10-16 기준 활성 공고 9,588건 중 426건(4%)이 이미 지났는데 그대로 추천에 올라왔다.
-- 값이 없는 공고(미수집·해당 없음)는 종전처럼 통과. 평가 하네스(evaluate_recommender.fetch_active_notices)도
-- 같은 조건을 쓴다 (시점 t 기준).
--
-- 0048 과 같은 양식: drop 후 create (본문 한 줄 추가, 시그니처 동일).

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
      and (b.bid_qlfct_rgst_dt is null or b.bid_qlfct_rgst_dt > now())
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
      and (b.bid_qlfct_rgst_dt is null or b.bid_qlfct_rgst_dt > now())
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
