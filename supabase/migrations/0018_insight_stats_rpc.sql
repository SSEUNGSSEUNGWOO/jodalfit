-- ====================================================================
-- 인사이트 집계 RPC
--
-- PostgREST가 aggregate 함수 호출을 막아둬서(PGRST123) 클라이언트에서
-- 평균·분위수를 낼 수 없다. 인사이트 자동 생성(jobs/weekly_insight)이
-- 쓸 집계를 함수로 노출한다.
--
-- 원천은 award_results(개찰 결과) 41만 건. 그중 낙찰 + 투찰율 있는 건이
-- 약 19.5만 건이며, 이 표본이 "실제로 몇 %에 낙찰됐는가"의 근거다.
-- ====================================================================

-- 업무구분 × 금액대별 낙찰 투찰율 분포.
-- 폭(p90-p10)이 좁으면 가격으로 승부가 안 나는 시장, 넓으면 가격 전략이
-- 실제로 작동하는 시장이라는 뜻이다.
create or replace function insight_bid_rate_stats()
returns table (
  bsns_div_nm  text,
  amt_bucket   text,
  bucket_order int,
  n            bigint,
  avg_rate     numeric,
  p10          numeric,
  p50          numeric,
  p90          numeric,
  min_rate     numeric,
  max_rate     numeric
)
language sql
stable
as $$
  select
    a.bsns_div_nm,
    case
      when a.bid_amt <    100000000 then '1억 미만'
      when a.bid_amt <   1000000000 then '1억~10억'
      when a.bid_amt <  10000000000 then '10억~100억'
      else                               '100억 이상'
    end,
    case
      when a.bid_amt <    100000000 then 1
      when a.bid_amt <   1000000000 then 2
      when a.bid_amt <  10000000000 then 3
      else                               4
    end,
    count(*)::bigint,
    round(avg(a.bid_rate)::numeric, 2),
    round((percentile_cont(0.1) within group (order by a.bid_rate))::numeric, 2),
    round((percentile_cont(0.5) within group (order by a.bid_rate))::numeric, 2),
    round((percentile_cont(0.9) within group (order by a.bid_rate))::numeric, 2),
    round(min(a.bid_rate)::numeric, 2),
    round(max(a.bid_rate)::numeric, 2)
  from award_results a
  where a.is_winner
    and a.bid_rate is not null
    -- 원천에 0이나 수천% 같은 이상치가 섞여 있어 상식 범위로 자른다.
    and a.bid_rate between 50 and 120
    and a.bid_amt is not null
    and a.bid_amt > 0
    and a.bsns_div_nm is not null
  group by 1, 2, 3
  having count(*) >= 30      -- 표본 30건 미만 구간은 통계로 쓰지 않는다
  order by 1, 3;
$$;

comment on function insight_bid_rate_stats is
  '업무구분 × 금액대별 낙찰 투찰율 분포(평균·p10·p50·p90). 인사이트 analysis 글의 근거.';


-- 공고당 참여 업체 수 = 경쟁 강도.
-- award_results는 개찰 참여자를 순위별로 모두 담으므로 공고별 행 수가 곧 참여 수다.
create or replace function insight_competition_stats()
returns table (
  bsns_div_nm   text,
  amt_bucket    text,
  bucket_order  int,
  notices       bigint,
  avg_bidders   numeric,
  p50_bidders   numeric,
  p90_bidders   numeric
)
language sql
stable
as $$
  with per_notice as (
    select
      a.bid_ntce_no,
      a.bid_ntce_ord,
      max(a.bsns_div_nm)                                    as bsns_div_nm,
      max(a.bid_amt) filter (where a.is_winner)              as win_amt,
      count(*)::numeric                                      as bidders
    from award_results a
    where a.bsns_div_nm is not null
    group by a.bid_ntce_no, a.bid_ntce_ord
  )
  select
    p.bsns_div_nm,
    case
      when p.win_amt <    100000000 then '1억 미만'
      when p.win_amt <   1000000000 then '1억~10억'
      when p.win_amt <  10000000000 then '10억~100억'
      else                               '100억 이상'
    end,
    case
      when p.win_amt <    100000000 then 1
      when p.win_amt <   1000000000 then 2
      when p.win_amt <  10000000000 then 3
      else                               4
    end,
    count(*)::bigint,
    round(avg(p.bidders), 1),
    round((percentile_cont(0.5) within group (order by p.bidders))::numeric, 1),
    round((percentile_cont(0.9) within group (order by p.bidders))::numeric, 1)
  from per_notice p
  where p.win_amt is not null
    and p.win_amt > 0
  group by 1, 2, 3
  having count(*) >= 30
  order by 1, 3;
$$;

comment on function insight_competition_stats is
  '업무구분 × 금액대별 공고당 참여 업체 수(경쟁 강도). 인사이트 analysis 글의 근거.';
