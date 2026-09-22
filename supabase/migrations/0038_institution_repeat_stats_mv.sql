-- ====================================================================
-- 기관별 반복거래 통계를 하루 한 번 미리 계산한다
--
-- institution_repeat_stats(0015) 는 추천 1회마다 contracts 47만 행에서 후보 공고
-- 기관 수십 곳의 2년치를 다시 집계했다. 2026-09-22 Server-Timing 실측(Railway 싱가포르)
-- 에서 이 한 단계가 추천 전체의 57~71%(4.1~6.4초)였고, 종종 statement timeout(8초)
-- 까지 가서 결과 없이 degrade 됐다. 그런데 값은 하루 한 번 수집될 때만 바뀐다.
--
-- 기관은 약 8천 곳이라 MV 는 8천 행이다. 조회는 PK 룩업이 된다.
-- 창은 recommender/collaborative.py 의 STATS_YEARS(=2) 와 맞춘다.
-- ====================================================================

create materialized view if not exists institution_repeat_stats_mv as
select c.dmnd_instt_nm,
       count(*)::int                                 as total,
       count(distinct c.rprsnt_corp_bizrno_norm)::int as distinct_winners
from contracts c
where c.dmnd_instt_nm is not null
  and c.cntrct_cncls_date >= current_date - interval '2 years'
group by c.dmnd_instt_nm
with no data;

-- refresh ... concurrently 에 필요
create unique index if not exists institution_repeat_stats_mv_instt_idx
  on institution_repeat_stats_mv (dmnd_instt_nm);

grant select on institution_repeat_stats_mv to service_role;

create or replace function public.institution_repeat_stats_cached(p_instts text[])
returns table(dmnd_instt_nm text, total integer, distinct_winners integer)
language sql
stable
as $function$
  select m.dmnd_instt_nm, m.total, m.distinct_winners
  from institution_repeat_stats_mv m
  where m.dmnd_instt_nm = any(p_instts);
$function$;

-- 첫 채우기 — MCP(execute_sql)는 트랜잭션 안이고 클라이언트 타임아웃이 짧아 무거운 작업을
-- 맡기면 끊긴 뒤에도 서버에서 계속 돌며 락을 잡는다(2026-09-21 사이트맵 MV 10분 사건).
-- pg_cron 세션에서 1회 돌리고 스스로 해제한다. pg_cron 은 같은 잡을 겹쳐 실행하지 않는다.
select cron.schedule(
  'populate-institution-repeat-stats-once',
  '* * * * *',
  $$set statement_timeout = 0;
    refresh materialized view institution_repeat_stats_mv;
    select cron.unschedule('populate-institution-repeat-stats-once');$$
);

-- 매일 갱신 — KST 07:30 (UTC 22:30). daily-sync(KST 05:00) 로 계약이 들어온 뒤이고,
-- 기존 MV 갱신(KST 08:00·08:10)과 겹치지 않게 앞에 둔다.
select cron.schedule(
  'refresh-institution-repeat-stats',
  '30 22 * * *',
  $$set statement_timeout = 0; refresh materialized view concurrently institution_repeat_stats_mv$$
);
