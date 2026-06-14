-- v0.3: 단계 풀 확장 — 사전규격(골든타임) + 발주계획(선행지표) 매칭 RPC
-- 추천 엔진이 입찰공고만 보던 한계 해소: 같은 회사·키워드 임베딩으로 세 단계 모두 매칭.

-- 사전규격 매칭
create or replace function match_pre_specs(
  query_embedding vector(1536),
  match_count int default 50
)
returns table (
  bf_spec_rgst_no    text,
  bid_ntce_no_list   text,
  prdct_clsfc_no_nm  text,
  bsns_div_nm        text,
  sw_biz_obj_yn      char(1),
  asign_bdgt_amt     bigint,
  rgst_dt            timestamptz,
  opnin_rgst_clse_dt timestamptz,
  order_instt_nm     text,
  rl_dminstt_nm      text,
  prdct_dtl_list     text,
  ref_no             text,
  similarity         real
)
language sql
stable
as $$
  select s.bf_spec_rgst_no, s.bid_ntce_no_list, s.prdct_clsfc_no_nm, s.bsns_div_nm,
         s.sw_biz_obj_yn, s.asign_bdgt_amt, s.rgst_dt, s.opnin_rgst_clse_dt,
         s.order_instt_nm, s.rl_dminstt_nm, s.prdct_dtl_list, s.ref_no,
         (1 - (s.embedding <=> query_embedding))::real as similarity
  from pre_specs s
  where s.embedding is not null
  order by s.embedding <=> query_embedding
  limit match_count;
$$;


-- 발주계획 매칭
create or replace function match_order_plans(
  query_embedding vector(1536),
  match_count int default 50
)
returns table (
  order_plan_unty_no text,
  biz_nm             text,
  bsns_div_nm        text,
  bsns_ty_nm         text,
  order_year         text,
  order_mnth         text,
  cntrct_mthd_nm     text,
  order_instt_nm     text,
  totlmng_instt_nm   text,
  sum_order_amt      bigint,
  prdct_clsfc_no_nm  text,
  usg_cntnts         text,
  spec_cntnts        text,
  ntice_dt           timestamptz,
  similarity         real
)
language sql
stable
as $$
  select o.order_plan_unty_no, o.biz_nm, o.bsns_div_nm, o.bsns_ty_nm,
         o.order_year, o.order_mnth, o.cntrct_mthd_nm,
         o.order_instt_nm, o.totlmng_instt_nm, o.sum_order_amt,
         o.prdct_clsfc_no_nm, o.usg_cntnts, o.spec_cntnts, o.ntice_dt,
         (1 - (o.embedding <=> query_embedding))::real as similarity
  from order_plans o
  where o.embedding is not null
  order by o.embedding <=> query_embedding
  limit match_count;
$$;
