-- ====================================================================
-- 발주기관별 과거 낙찰 평균 투찰률을 하루 한 번 미리 계산한다
--
-- 회사 페이지 추천 카드의 "이 기관 비슷한 공고 평균 XX% (n건)". 예전엔
-- frontend lib/company.ts::fetchPeerRateByInstitution 이 요청마다 bid_notices 에서 기관
-- 공고를 최대 5천 건 가져오고, 그 번호로 award_results 를 500개씩 순차 조회해 JS 에서
-- 평균을 냈다. 2026-09-22 Server-Timing 실측에서 1.3~1.9초 — 라우트 끝단의 약 45%.
--
-- 부수 효과로 정확해진다: 예전엔 limit(5000) 에서 잘려 큰 기관은 표본 일부로만
-- 평균을 냈다. MV 는 전 기간 전체를 본다.
-- bid_notices 의 PK 가 (bid_ntce_no, bid_ntce_ord) 라 조인이 행을 부풀리지 않는다.
-- ====================================================================

create materialized view if not exists institution_bid_rate_mv as
select bn.dmnd_instt_nm,
       avg(ar.bid_rate)::float8 as avg_rate,
       count(*)::int            as n
from award_results ar
join bid_notices bn
  on bn.bid_ntce_no = ar.bid_ntce_no
 and bn.bid_ntce_ord = ar.bid_ntce_ord
where ar.is_winner
  and ar.bid_rate is not null
  and bn.dmnd_instt_nm is not null
group by bn.dmnd_instt_nm
with no data;

create unique index if not exists institution_bid_rate_mv_instt_idx
  on institution_bid_rate_mv (dmnd_instt_nm);

grant select on institution_bid_rate_mv to service_role;

-- 첫 채우기는 pg_cron 1회성 잡 (0038 과 같은 이유 — MCP 는 무거운 작업을 맡기면 끊긴 뒤에도
-- 서버에서 계속 돌며 락을 잡는다).
--
-- 주의(2026-09-22 실제로 겪음): 최초 채우기는 concurrently 가 안 돼 일반 refresh 라 MV 에
-- 배타 락을 잡는다. 그동안 이 MV 를 읽는 요청은 "not populated" 에러로 바로 튕기지 않고
-- 락을 기다리다 타임아웃한다 — 이 조인은 수 분 걸려 회사 추천 카드가 16초씩 멈췄다.
-- 다음에 무거운 MV 를 새로 붙일 땐 다른 이름으로 `create ... with data` 해 두고 다 채워지면
-- rename 으로 교체해, 읽는 쪽이 락을 볼 일 없게 할 것.
select cron.schedule(
  'populate-institution-bid-rate-once',
  '* * * * *',
  $$set statement_timeout = 0;
    refresh materialized view institution_bid_rate_mv;
    select cron.unschedule('populate-institution-bid-rate-once');$$
);

-- 매일 갱신 — KST 07:40 (UTC 22:40). 0038(07:30) 뒤, 기존 MV 갱신(08:00) 앞.
select cron.schedule(
  'refresh-institution-bid-rate',
  '40 22 * * *',
  $$set statement_timeout = 0; refresh materialized view concurrently institution_bid_rate_mv$$
);
