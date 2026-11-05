-- supabase/migrations/0067_gemini_embedding_space.sql
-- 세 번째 임베딩 공간 `gemini`(Google gemini-embedding-001, outputDimensionality 768) — 0045(kure) 와 같은 꼴로
-- 4개 표에 `embedding_g vector(768)` + `embedded_g_at`, 캐시 표에 `embedding_g`, RPC `_g` 변형 9개를 덧붙인다.
--
-- 근거: docs/recommender/exp-2026-11-04-embedding-rematch.md — final@20 3시점 평균 0.513(KURE) → 0.580(Gemini 768d),
-- 10/1 홀드아웃 0.640 → 0.689. 계획: docs/superpowers/plans/2026-11-05-gemini-embedding-switch.md.
--
-- 운영 영향 없음: 열 추가는 nullable·기본값 없음이라 메타데이터만 바뀌고, 함수는 전부 신규. 운영이 읽는 `_k` 열·함수는 그대로.
-- 본문은 운영 DB 의 `_k` 정의(pg_get_functiondef, 2026-11-05)를 복사해 컬럼명·차원만 바꿨다.
-- 인덱스는 여기서 만들지 않는다 — 백필 뒤 0067-b(파일 하단) 를 concurrently 로.
--
-- 2026-11-05 psycopg 로 운영에 적용(기록용).

begin;

set local lock_timeout = '5s';  -- 추천 RPC(8s 상한)와 겹쳐도 기다리다 포기하게 — 운영을 막지 않는다

alter table bid_notices     add column if not exists embedding_g vector(768), add column if not exists embedded_g_at timestamptz;
alter table companies       add column if not exists embedding_g vector(768), add column if not exists embedded_g_at timestamptz;
alter table pre_specs       add column if not exists embedding_g vector(768), add column if not exists embedded_g_at timestamptz;
alter table order_plans     add column if not exists embedding_g vector(768), add column if not exists embedded_g_at timestamptz;
alter table text_embeddings add column if not exists embedding_g vector(768);  -- (space='gemini', sha1) 행은 이 열만 채운다
alter table text_embeddings alter column embedding drop not null;              -- 0046 은 not null — gemini 행이 23502 로 막혔다(2026-11-05 19:05)

-- ====================================================================
-- match_bid_notices_g — 운영 match_bid_notices_k(0049 최신: product_codes·참가자격 등록 마감) 복사
-- ====================================================================
drop function if exists match_bid_notices_g(vector, int, date, text, date, text[], text[]);

create function match_bid_notices_g(
  query_embedding vector(768),
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
  rgn_lmt_yn char(1), prtcpt_psbl_rgn_nm text, indstryty_lmt_yn char(1),
  bid_ntce_url text, similarity real
)
language sql
stable
as $$
  with active as materialized (
    select b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
           b.bid_ntce_date, b.bid_clse_date, b.openg_date,
           b.presmpt_prce, b.ntce_instt_nm, b.dmnd_instt_nm,
           b.bidprc_psbl_indstryty_nm, b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm,
           b.indstryty_lmt_yn, b.bid_ntce_url, b.embedding_g
    from bid_notices b
    where b.embedding_g is not null
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
         (1 - (a.embedding_g <=> query_embedding))::real as similarity
  from active a
  order by a.embedding_g <=> query_embedding
  limit match_count;
$$;

-- ====================================================================
-- match_pre_specs_g
-- ====================================================================
drop function if exists match_pre_specs_g(vector, int, date);

create function match_pre_specs_g(
  query_embedding vector(768),
  match_count int default 50,
  min_opnin_clse_date date default null
)
returns table (
  bf_spec_rgst_no text, bid_ntce_no_list text, prdct_clsfc_no_nm text, bsns_div_nm text,
  sw_biz_obj_yn char(1), asign_bdgt_amt bigint, rgst_dt timestamptz, opnin_rgst_clse_dt timestamptz,
  order_instt_nm text, rl_dminstt_nm text, prdct_dtl_list text, ref_no text, similarity real
)
language sql
stable
as $$
  select s.bf_spec_rgst_no, s.bid_ntce_no_list, s.prdct_clsfc_no_nm, s.bsns_div_nm,
         s.sw_biz_obj_yn, s.asign_bdgt_amt, s.rgst_dt, s.opnin_rgst_clse_dt,
         s.order_instt_nm, s.rl_dminstt_nm, s.prdct_dtl_list, s.ref_no,
         (1 - (s.embedding_g <=> query_embedding))::real as similarity
  from pre_specs s
  where s.embedding_g is not null
    and (
      min_opnin_clse_date is null
      or s.opnin_rgst_clse_dt is null   -- 데이터 누락은 보수적으로 포함
      or s.opnin_rgst_clse_dt::date >= min_opnin_clse_date
    )
  order by s.embedding_g <=> query_embedding
  limit match_count;
$$;

-- ====================================================================
-- match_order_plans_g — 0059(공고 전환된 계획 제외) 복사
-- ====================================================================
drop function if exists match_order_plans_g(vector, int);

create function match_order_plans_g(
  query_embedding vector(768),
  match_count int default 50
)
returns table (
  order_plan_unty_no text, biz_nm text, bsns_div_nm text, bsns_ty_nm text,
  order_year text, order_mnth text, cntrct_mthd_nm text, order_instt_nm text,
  totlmng_instt_nm text, sum_order_amt bigint, prdct_clsfc_no_nm text,
  usg_cntnts text, spec_cntnts text, ntice_dt timestamptz, bid_ntce_no_list text, similarity real
)
language sql
stable
as $$
  select o.order_plan_unty_no, o.biz_nm, o.bsns_div_nm, o.bsns_ty_nm,
         o.order_year, o.order_mnth, o.cntrct_mthd_nm,
         o.order_instt_nm, o.totlmng_instt_nm, o.sum_order_amt,
         o.prdct_clsfc_no_nm, o.usg_cntnts, o.spec_cntnts, o.ntice_dt,
         o.bid_ntce_no_list,
         (1 - (o.embedding_g <=> query_embedding))::real as similarity
    from order_plans o
   where o.embedding_g is not null
     and coalesce(o.bid_ntce_no_list, '') = ''   -- 이미 공고가 뜬 계획은 선행지표가 아니다
   order by o.embedding_g <=> query_embedding
   limit match_count;
$$;

-- ====================================================================
-- match_companies_g — (운영은 peer 탐색을 꺼 두어 안 부르지만 공간 대칭을 위해 둔다)
-- ====================================================================
drop function if exists match_companies_g(vector, int, text);

create function match_companies_g(
  query_embedding vector(768),
  match_count int default 20,
  exclude_bizrno_norm text default null
)
returns table (bizrno text, bizrno_norm text, corp_nm text, similarity real)
language sql
stable
as $$
  select c.bizrno, c.bizrno_norm, c.corp_nm,
         (1 - (c.embedding_g <=> query_embedding))::real as similarity
  from companies c
  where c.embedding_g is not null
    and not c.is_restricted
    and (exclude_bizrno_norm is null or c.bizrno_norm <> exclude_bizrno_norm)
  order by c.embedding_g <=> query_embedding
  limit match_count;
$$;

-- ====================================================================
-- similar_notice_awardees_g — halfvec(768) + ivfflat.probes 10 (0067-b 인덱스와 짝)
-- ====================================================================
drop function if exists similar_notice_awardees_g(text, int, int, int);

create function similar_notice_awardees_g(
  p_bizrno_norm    text,
  p_similar_pool   int default 60,
  p_top_n          int default 10,
  p_history_limit  int default 30
)
returns table(bizrno text, corp_nm text, encounter_count int, sample_notice_names text[])
language plpgsql
stable
as $$
declare
  v_avg halfvec(768);
begin
  select avg(bn.embedding_g)::halfvec(768)
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
    where bn.embedding_g is not null;

  if v_avg is null then
    return;
  end if;

  perform set_config('ivfflat.probes', '10', true);

  return query
  with similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2
    order by bn2.embedding_g::halfvec(768) <=> v_avg
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

-- ====================================================================
-- update_*_embeddings_g — 잡의 배치 쓰기 (0046 `_k` 와 동일, 열만 다름)
-- ====================================================================
create or replace function update_bid_notice_embeddings_g(updates jsonb) returns int
language plpgsql as $$
declare rec record; cnt int := 0;
begin
  for rec in select * from jsonb_to_recordset(updates) as x(bid_ntce_no text, bid_ntce_ord text, embedding text, embedded_at timestamptz)
  loop
    update bid_notices set embedding_g = rec.embedding::vector, embedded_g_at = rec.embedded_at
     where bid_ntce_no = rec.bid_ntce_no and bid_ntce_ord = rec.bid_ntce_ord;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end; $$;

create or replace function update_pre_specs_embeddings_g(updates jsonb) returns int
language plpgsql as $$
declare rec record; cnt int := 0;
begin
  for rec in select * from jsonb_to_recordset(updates) as x(bf_spec_rgst_no text, embedding text, embedded_at timestamptz)
  loop
    update pre_specs set embedding_g = rec.embedding::vector, embedded_g_at = rec.embedded_at
     where bf_spec_rgst_no = rec.bf_spec_rgst_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end; $$;

create or replace function update_order_plans_embeddings_g(updates jsonb) returns int
language plpgsql as $$
declare rec record; cnt int := 0;
begin
  for rec in select * from jsonb_to_recordset(updates) as x(order_plan_unty_no text, embedding text, embedded_at timestamptz)
  loop
    update order_plans set embedding_g = rec.embedding::vector, embedded_g_at = rec.embedded_at
     where order_plan_unty_no = rec.order_plan_unty_no;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end; $$;

create or replace function update_company_embeddings_g(updates jsonb) returns int
language plpgsql as $$
declare rec record; cnt int := 0;
begin
  for rec in select * from jsonb_to_recordset(updates) as x(bizrno text, embedding text, embedded_at timestamptz)
  loop
    update companies set embedding_g = rec.embedding::vector, embedded_g_at = rec.embedded_at
     where bizrno = rec.bizrno;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end; $$;

notify pgrst, 'reload schema';

commit;

-- ====================================================================
-- 0067-b (백필 뒤, 각각 따로 실행 — concurrently 는 트랜잭션 밖)
-- ====================================================================
-- create index concurrently if not exists bid_notices_embedding_g_ivf_idx
--   on bid_notices using ivfflat ((embedding_g::halfvec(768)) halfvec_cosine_ops) with (lists = 600);
-- create index concurrently if not exists pre_specs_embedding_g_idx   on pre_specs   using hnsw (embedding_g vector_cosine_ops);
-- create index concurrently if not exists order_plans_embedding_g_idx on order_plans using hnsw (embedding_g vector_cosine_ops);
-- companies: 운영이 match_companies 를 안 부르고(pipeline.py 주석) `_k` 인덱스도 idx_scan 0 — 만들지 않는다.
