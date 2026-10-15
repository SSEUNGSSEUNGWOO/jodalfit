-- 임베딩 모델 전환 실험(docs/recommender/exp-2026-10-15-embedding-model.md): KURE-v1(1024d)이
-- OpenAI text-embedding-3-small(1536d)보다 dense 0.55→0.63, final@30 0.395→0.438 로 우세.
--
-- 두 공간을 병행한다. 기존 `embedding vector(1536)` 컬럼·RPC는 그대로 두고, 4개 테이블
-- (bid_notices/companies/pre_specs/order_plans)에 `embedding_k vector(1024)` 컬럼과 그 전용
-- RPC `_k` 변형을 추가한다. 백엔드 `settings.embed_space`(openai|kure)가 어느 컬럼·RPC·
-- 임베딩 함수를 쓸지 고른다 — 전환/롤백이 환경변수 하나로 끝난다. 본문은 각 함수의 최신
-- 정의(0044·0010·0009·0015·0037)를 그대로 복사하고 컬럼명·벡터 차원만 바꿨다.
--
-- create or replace 가 아니라 drop 후 create 인 이유: 이 함수들은 지금 처음 생기므로 arity
-- 충돌은 없지만, 이 마이그레이션 파일을 재실행했을 때(이미 적용된 환경에서 다시 돌리는 실수)
-- create function 은 "already exists" 로 죽는다. drop if exists 로 재실행을 멱등하게 만든다.
--
-- 인덱스는 여기서 만들지 않는다 — embedding_k 는 전부 null 상태로 시작하고, 백필(Task 4,
-- 노트북 GPU)이 끝난 뒤에야 인덱스가 의미 있다. 파일 하단 "0045-b" 주석 블록을 백필 후 실행.

begin;

alter table bid_notices  add column if not exists embedding_k vector(1024);
alter table companies    add column if not exists embedding_k vector(1024);
alter table pre_specs    add column if not exists embedding_k vector(1024);
alter table order_plans  add column if not exists embedding_k vector(1024);

-- ====================================================================
-- match_bid_notices_k — 0044 본문 복사 (업종 채널 + max_clse_date 포함, 최신 정의)
-- ====================================================================

drop function if exists match_bid_notices_k(vector, int, date, text, date, text[]);

create function match_bid_notices_k(
  query_embedding vector(1024),
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
           b.indstryty_lmt_yn, b.bid_ntce_url, b.embedding_k
    from bid_notices b
    where b.embedding_k is not null
      and b.bid_clse_date >= coalesce(min_clse_date, current_date)
      and (max_clse_date is null or b.bid_clse_date <= max_clse_date)
      and (bsns_div_filter is null or b.bsns_div_nm = bsns_div_filter)
      and (industry_names is null
           or exists (select 1 from unnest(industry_names) n
                      where position(n in b.bidprc_psbl_indstryty_nm) > 0))
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

-- ====================================================================
-- match_pre_specs_k — 0010 본문 복사 (의견 마감일 필터 포함, 최신 정의)
-- ====================================================================

drop function if exists match_pre_specs_k(vector, int, date);

create function match_pre_specs_k(
  query_embedding vector(1024),
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
         (1 - (s.embedding_k <=> query_embedding))::real as similarity
  from pre_specs s
  where s.embedding_k is not null
    and (
      min_opnin_clse_date is null
      or s.opnin_rgst_clse_dt is null   -- 데이터 누락은 보수적으로 포함
      or s.opnin_rgst_clse_dt::date >= min_opnin_clse_date
    )
  order by s.embedding_k <=> query_embedding
  limit match_count;
$$;

-- ====================================================================
-- match_order_plans_k — 0009 본문 복사 (이후 변경 없음, 최신 정의)
-- ====================================================================

drop function if exists match_order_plans_k(vector, int);

create function match_order_plans_k(
  query_embedding vector(1024),
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
         (1 - (o.embedding_k <=> query_embedding))::real as similarity
  from order_plans o
  where o.embedding_k is not null
  order by o.embedding_k <=> query_embedding
  limit match_count;
$$;

-- ====================================================================
-- match_companies_k — 0015 본문 복사 (이후 변경 없음, 최신 정의)
-- ====================================================================

drop function if exists match_companies_k(vector, int, text);

create function match_companies_k(
  query_embedding vector(1024),
  match_count int default 20,
  exclude_bizrno_norm text default null
)
returns table (
  bizrno text,
  bizrno_norm text,
  corp_nm text,
  similarity real
)
language sql
stable
as $$
  select c.bizrno, c.bizrno_norm, c.corp_nm,
         (1 - (c.embedding_k <=> query_embedding))::real as similarity
  from companies c
  where c.embedding_k is not null
    and not c.is_restricted
    and (exclude_bizrno_norm is null or c.bizrno_norm <> exclude_bizrno_norm)
  order by c.embedding_k <=> query_embedding
  limit match_count;
$$;

comment on function match_companies_k(vector, int, text) is
  '회사 벡터(KURE-v1, 1024d) 코사인 유사도 top-k. match_companies 의 embedding_k 변형.';

-- ====================================================================
-- similar_notice_awardees_k — 0037 본문 복사 (optout 제외 + bizrno_norm 매칭, 최신 정의)
-- halfvec 캐스팅·ivfflat.probes 는 0045-b 인덱스(백필 뒤 생성)와 짝을 맞춘 것 — 인덱스가
-- 아직 없어도 함수는 순차 스캔으로 정상 동작한다(정확도 동일, 속도만 느림).
-- ====================================================================

drop function if exists similar_notice_awardees_k(text, int, int, int);

create function similar_notice_awardees_k(
  p_bizrno_norm    text,
  p_similar_pool   int default 60,
  p_top_n          int default 10,
  p_history_limit  int default 30
)
returns table(
  bizrno              text,
  corp_nm             text,
  encounter_count     int,
  sample_notice_names text[]
)
language plpgsql
stable
as $$
declare
  v_avg halfvec(1024);
begin
  select avg(bn.embedding_k)::halfvec(1024)
    into v_avg
    from (
      select ar.bid_ntce_no, ar.bid_ntce_ord
      from award_results ar
      where ar.bizrno_norm = p_bizrno_norm
        and ar.is_winner
      order by ar.bid_ntce_no desc
      limit p_history_limit
    ) cn
    join bid_notices bn
      on bn.bid_ntce_no = cn.bid_ntce_no
     and bn.bid_ntce_ord = cn.bid_ntce_ord
    where bn.embedding_k is not null;

  if v_avg is null then
    return;
  end if;

  perform set_config('ivfflat.probes', '10', true);

  return query
  with similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2
    order by bn2.embedding_k::halfvec(1024) <=> v_avg
    limit p_similar_pool
  ),
  competitor_awards as (
    select ar.bizrno_norm, ar.corp_nm, sn.bid_ntce_nm
    from similar_notices sn
    join award_results ar
      on ar.bid_ntce_no = sn.bid_ntce_no
     and ar.bid_ntce_ord = sn.bid_ntce_ord
    where ar.is_winner
      and ar.bizrno_norm is not null
      and ar.bizrno_norm <> ''
      and ar.bizrno_norm <> p_bizrno_norm
      and not exists (
        select 1 from companies c
        where c.bizrno_norm = ar.bizrno_norm
          and c.optout_at is not null
      )
  )
  select
    ca.bizrno_norm as bizrno,
    (array_agg(ca.corp_nm order by length(ca.corp_nm) desc))[1] as corp_nm,
    count(*)::int as encounter_count,
    (array_agg(distinct ca.bid_ntce_nm))[1:3] as sample_notice_names
  from competitor_awards ca
  group by ca.bizrno_norm
  order by encounter_count desc
  limit p_top_n;
end;
$$;

comment on function similar_notice_awardees_k(text, int, int, int) is
  '회사 낙찰 이력의 평균 임베딩(KURE-v1, embedding_k)으로 유사 공고 풀 → 그 공고들 낙찰자 집계. similar_notice_awardees 의 _k 변형.';

notify pgrst, 'reload schema';

commit;

-- ====================================================================
-- 0045-b (백필 뒤 실행) — embedding_k 인덱스
--
-- 백필(Task 4, 노트북 GPU) 전에 인덱스를 만들면 빈 컬럼 기준으로 통계가 잡히고,
-- bid_notices 는 34만 행 규모라 HNSW 빌드가 메모리 부족으로 실패한 전례가 있다(0032).
-- 백필이 끝난 뒤 Dashboard SQL Editor 에서 주석을 풀고 실행.
-- ====================================================================

-- bid_notices: 0032 와 동일한 ivfflat halfvec 패턴 (HNSW 는 이 테이블 규모에서 빌드 실패 전례).
-- create index if not exists bid_notices_embedding_k_ivf_idx
--   on bid_notices using ivfflat ((embedding_k::halfvec(1024)) halfvec_cosine_ops)
--   with (lists = 600);

-- pre_specs / order_plans: 0001 원 정의와 동일한 hnsw (테이블 규모가 작아 HNSW 빌드 가능).
-- create index if not exists pre_specs_embedding_k_idx
--   on pre_specs using hnsw (embedding_k vector_cosine_ops);
-- create index if not exists order_plans_embedding_k_idx
--   on order_plans using hnsw (embedding_k vector_cosine_ops);

-- companies: 0031 방식 — bid_notices 와 달리 테이블 규모가 작아(6만 행대) HNSW 그대로 유지.
-- create index if not exists companies_embedding_k_idx
--   on companies using hnsw (embedding_k vector_cosine_ops);
