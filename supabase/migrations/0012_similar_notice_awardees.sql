-- ====================================================================
-- similar_notice_awardees: 유사 공고 낙찰자 = "상시 경쟁자 후보"
--
-- 나라장터 공개 API가 참가업체(2순위 이하)를 안 주므로 실제 경쟁자는
-- 확보 불가. 우회로: 회사 낙찰 이력의 평균 임베딩으로 유사 공고를 찾고
-- 그 공고들의 낙찰자를 집계 = "이 회사가 뛰는 시장의 상시 플레이어".
--
-- 성능 최적화 (v2):
--   v1(lateral join 반복)이 statement timeout(8s) 초과 → 평균 임베딩 접근으로
--   HNSW 검색을 1회로 단축. 회사가 여러 분야를 뛰면 평균이 흐릿해지지만,
--   대부분 케이스에서 정확도 손실보다 안정성 이득이 큼.
-- ====================================================================

-- v1 파라미터명(p_similar_k)에서 v2(p_similar_pool)로 변경되어
-- CREATE OR REPLACE로는 덮을 수 없음. 명시적 DROP 후 재생성.
drop function if exists similar_notice_awardees(text, int, int, int);

create or replace function similar_notice_awardees(
  p_bizrno_norm    text,
  p_similar_pool   int default 60,  -- 유사 공고 풀 크기 (top_n의 6배 정도 권장)
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
    where ar.bizrno = p_bizrno_norm
      and ar.is_winner
    order by ar.bid_ntce_no desc
    limit p_history_limit
  ),
  company_avg as (
    -- 회사 낙찰 공고들의 평균 임베딩. pgvector avg() 사용.
    select avg(bn.embedding)::vector(1536) as avg_emb
    from company_notices cn
    join bid_notices bn
      on bn.bid_ntce_no = cn.bid_ntce_no
     and bn.bid_ntce_ord = cn.bid_ntce_ord
    where bn.embedding is not null
  ),
  similar_notices as (
    -- HNSW 인덱스로 한 번의 검색으로 유사 공고 풀 확보.
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2, company_avg ca
    where bn2.embedding is not null
      and ca.avg_emb is not null
    order by bn2.embedding <=> ca.avg_emb
    limit p_similar_pool
  ),
  competitor_awards as (
    select ar.bizrno, ar.corp_nm, sn.bid_ntce_nm
    from similar_notices sn
    join award_results ar
      on ar.bid_ntce_no = sn.bid_ntce_no
     and ar.bid_ntce_ord = sn.bid_ntce_ord
    where ar.is_winner
      and ar.bizrno is not null
      and ar.bizrno <> p_bizrno_norm
  )
  select
    ca.bizrno,
    (array_agg(ca.corp_nm order by length(ca.corp_nm) desc))[1] as corp_nm,
    count(*)::int as encounter_count,
    (array_agg(distinct ca.bid_ntce_nm))[1:3] as sample_notice_names
  from competitor_awards ca
  group by ca.bizrno
  order by encounter_count desc
  limit p_top_n;
$$;

comment on function similar_notice_awardees(text, int, int, int) is
  '회사 낙찰 이력의 평균 임베딩으로 유사 공고 풀 → 그 공고들 낙찰자 집계. "유사 시장 상시 플레이어" 프로파일.';
