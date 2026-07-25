-- ====================================================================
-- fix: similar_notice_awardees가 award_results.bizrno(원본, 하이픈 가능)와
-- p_bizrno_norm(10자리 정규화)을 비교해서 매칭 실패 → 모든 회사에서 빈 결과.
-- 정규화 컬럼 bizrno_norm으로 통일.
-- ====================================================================

drop function if exists similar_notice_awardees(text, int, int, int);

create or replace function similar_notice_awardees(
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
language sql
stable
as $$
  with company_notices as (
    select ar.bid_ntce_no, ar.bid_ntce_ord
    from award_results ar
    where ar.bizrno_norm = p_bizrno_norm
      and ar.is_winner
    order by ar.bid_ntce_no desc
    limit p_history_limit
  ),
  company_avg as (
    select avg(bn.embedding)::vector(1536) as avg_emb
    from company_notices cn
    join bid_notices bn
      on bn.bid_ntce_no = cn.bid_ntce_no
     and bn.bid_ntce_ord = cn.bid_ntce_ord
    where bn.embedding is not null
  ),
  similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2, company_avg ca
    where bn2.embedding is not null
      and ca.avg_emb is not null
    order by bn2.embedding <=> ca.avg_emb
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
$$;

comment on function similar_notice_awardees(text, int, int, int) is
  '회사 낙찰 이력의 평균 임베딩으로 유사 공고 풀 → 그 공고들 낙찰자 집계. "유사 시장 상시 플레이어" 프로파일. (0013: bizrno_norm 매칭 수정)';
