-- 0013의 similar_notice_awardees(경쟁사 후보, 회사 페이지마다 호출)는 회사 평균 벡터를 CTE 크로스조인으로
-- 넘겨서 플래너가 HNSW(bid_notices_embedding_idx)를 못 쓰고 공고 34만 건을 브루트포스했다.
-- 낙찰 이력이 있는 회사는 전부 8초 statement timeout에 잘렸고(프론트가 삼켜 빈 섹션), 그만큼
-- 회사 페이지 SSR이 매번 8초를 채웠다 (2026-09-18 실측: explain 이 90초에도 안 끝남).
--
-- 평균 벡터를 변수로 뽑은 뒤 `order by embedding <=> v_avg limit n` 으로 바꿔 인덱스를 태운다.
-- HNSW 는 ef_search(기본 40)개까지만 반환하므로 p_similar_pool 만큼 올린다. 결과는 근사 최근접.

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
language plpgsql
stable
as $$
declare
  v_avg vector(1536);
begin
  select avg(bn.embedding)::vector(1536)
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
    where bn.embedding is not null;

  if v_avg is null then
    return;
  end if;

  perform set_config('hnsw.ef_search', greatest(p_similar_pool, 40)::text, true);

  return query
  with similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2
    order by bn2.embedding <=> v_avg
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
end;
$$;
