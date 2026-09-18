-- bid_notices 벡터 인덱스를 HNSW → IVFFlat(halfvec) 으로 교체.
--
-- 배경 (2026-09-18): bid_notices_embedding_idx(HNSW)는 indisvalid=false 로 한 번도 안 쓰였고,
-- `reindex index concurrently` 로 다시 만들려니 34만 × 1536d 그래프(2GB+)가 maintenance_work_mem(256MB)을
-- 넘긴 뒤 디스크 단계에서 25분에 6MB 속도로 기어서 포기했다. 이 인스턴스(1GB급)에선 HNSW 전체 빌드가 불가능.
--
-- IVFFlat 은 k-means 표본만 메모리에 두고 나머지는 순차 스캔이라 메모리와 무관하게 수십 분이면 끝난다.
-- halfvec(2바이트) 표현식 인덱스로 크기를 절반(≈1GB)으로 줄인다. 검색 쪽도 같은 표현식으로 비교해야
-- 인덱스를 탄다 (similar_notice_awardees 아래 갱신). lists=600 ≈ sqrt(345k), probes=10 → 약 1.7% 스캔.
--
-- 프로덕션은 pg_cron 1회성 잡으로 `create index concurrently` 적용. 미적용 환경은 아래를 그대로 실행.

drop index if exists bid_notices_embedding_idx;  -- invalid HNSW 잔재 (330MB)

create index if not exists bid_notices_embedding_ivf_idx
  on bid_notices using ivfflat ((embedding::halfvec(1536)) halfvec_cosine_ops)
  with (lists = 600);

-- 0031 의 similar_notice_awardees 를 halfvec 표현식 + ivfflat.probes 로 갱신
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
  v_avg halfvec(1536);
begin
  select avg(bn.embedding)::halfvec(1536)
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

  perform set_config('ivfflat.probes', '10', true);

  return query
  with similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2
    order by bn2.embedding::halfvec(1536) <=> v_avg
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
