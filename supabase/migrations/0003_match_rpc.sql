-- pgvector 코사인 검색 + 회사 fuzzy 매칭 RPC

-- 회사 fuzzy 검색 (pg_trgm)
create or replace function find_companies(query_name text, max_count int default 5)
returns table (
  bizrno text,
  corp_nm text,
  english_nm text,
  ceo_nm text,
  similarity real
)
language sql
stable
as $$
  select c.bizrno, c.corp_nm, c.english_nm, c.ceo_nm,
         greatest(
           similarity(c.corp_nm, query_name),
           coalesce(similarity(c.english_nm, query_name), 0)
         )::real as similarity
  from companies c
  where (c.corp_nm % query_name or c.english_nm % query_name)
    and not c.is_restricted
  order by similarity desc
  limit max_count;
$$;


-- 입찰공고 매칭 (회사 벡터 → 신규 공고 코사인 검색)
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
  select b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
         b.bid_ntce_date, b.bid_clse_date, b.openg_date,
         b.presmpt_prce, b.ntce_instt_nm, b.dmnd_instt_nm,
         b.bidprc_psbl_indstryty_nm, b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm,
         b.indstryty_lmt_yn, b.bid_ntce_url,
         (1 - (b.embedding <=> query_embedding))::real as similarity
  from bid_notices b
  where b.embedding is not null
    and (min_clse_date is null or b.bid_clse_date >= min_clse_date)
    and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
  order by b.embedding <=> query_embedding
  limit match_count;
$$;
