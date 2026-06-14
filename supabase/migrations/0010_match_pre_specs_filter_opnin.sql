-- v0.3 픽스: match_pre_specs에 의견 마감일 필터 추가
-- 사용자 보고: "사전규격 단계 · 골든타임" 섹션에 마감 지난 사전규격이 나옴.
-- 골든타임 카피("의견 낼 수 있는 시점")와 충돌 → 마감 안 지난 것만 노출.

create or replace function match_pre_specs(
  query_embedding vector(1536),
  match_count int default 50,
  min_opnin_clse_date date default null
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
    and (
      min_opnin_clse_date is null
      or s.opnin_rgst_clse_dt is null   -- 데이터 누락은 보수적으로 포함
      or s.opnin_rgst_clse_dt::date >= min_opnin_clse_date
    )
  order by s.embedding <=> query_embedding
  limit match_count;
$$;
