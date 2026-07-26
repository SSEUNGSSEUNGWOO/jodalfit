-- ====================================================================
-- Phase 2 협업 필터링 RPC
-- 1) match_companies: 회사 벡터 → 유사 회사 top-k (피어 탐색)
-- 2) institution_repeat_stats: 기관별 계약 총건수·distinct 낙찰사
--    → 반복거래율(1 - distinct/total)로 "고정 거래처 기관" 판별
-- ====================================================================

create or replace function match_companies(
  query_embedding vector(1536),
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
         (1 - (c.embedding <=> query_embedding))::real as similarity
  from companies c
  where c.embedding is not null
    and not c.is_restricted
    and (exclude_bizrno_norm is null or c.bizrno_norm <> exclude_bizrno_norm)
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

comment on function match_companies(vector, int, text) is
  '회사 벡터 코사인 유사도 top-k. 협업 필터링의 피어 회사 탐색용.';


create index if not exists contracts_dmnd_instt_date_idx
  on contracts (dmnd_instt_nm, cntrct_cncls_date);

-- 참가업체(rank 2+) 행 조회용 — is_winner=false는 소수라 partial index 필요
-- (compute_company_vectors.fetch_active_bizrnos keyset 페이지네이션이 사용)
create index if not exists award_results_participant_bizrno_idx
  on award_results (bizrno) where is_winner = false;

create or replace function institution_repeat_stats(
  p_instts text[],
  p_since date
)
returns table (
  dmnd_instt_nm text,
  total int,
  distinct_winners int
)
language sql
stable
as $$
  select c.dmnd_instt_nm,
         count(*)::int as total,
         count(distinct c.rprsnt_corp_bizrno_norm)::int as distinct_winners
  from contracts c
  where c.dmnd_instt_nm = any(p_instts)
    and c.cntrct_cncls_date >= p_since
  group by c.dmnd_instt_nm;
$$;

comment on function institution_repeat_stats(text[], date) is
  '기관별 최근 계약 총건수와 distinct 낙찰사 수. 반복거래율 계산 재료.';
