-- 로그 지표에서 내부 SSR 호출과 실사용자를 분리한다.
--
-- 문제: search_logs·notice_events가 회사·공고 SEO 페이지의 서버 렌더링 호출까지
-- 같이 기록해 왔다. 2026-09-18 확인 — search_logs 최근 1,000건 중 982건이 내부
-- SSR(user_agent = 'node')이었고, notice_events는 누적 110만 건인데 그중 사용자
-- 행동(save)은 3건뿐이었다. "검색 8만 건" 같은 숫자를 지표로 쓸 수 없는 상태.
--
-- 조치:
--   1) 두 테이블에 source 컬럼 (user / internal / bot)
--   2) 기존 행 backfill — search_logs는 user_agent로 판정 가능, notice_events는
--      소급 판정이 불가능하므로 impression은 unknown으로 둔다
--   3) 실사용자만 보는 뷰 추가. 기존 뷰는 전체 기준이라 그대로 둔다
-- 백엔드는 X-Internal-Token(bot_guard와 같은 신호)으로 판정하며,
-- 내부 SSR의 impression은 아예 적재하지 않는다 (app/services/notice_events.py).

alter table search_logs   add column if not exists source text not null default 'user';
alter table notice_events add column if not exists source text not null default 'user';

-- 기존 행 backfill (default 'user'로 들어간 것을 실제 출처로 정정)
update search_logs
   set source = case
         when user_agent is null or btrim(user_agent) = '' then 'bot'
         when user_agent ilike 'node%' then 'internal'
         when user_agent ~* '(bot|spider|crawl|slurp|yeti|facebookexternalhit|bingpreview|headless|python-requests|httpx|aiohttp|curl/|wget/|go-http-client|okhttp|java/|scrapy|axios|node-fetch|undici|lighthouse|uptime)' then 'bot'
         else 'user'
       end
 where source = 'user';

-- notice_events는 user_agent를 남기지 않았다. impression은 대부분 내부 SSR이지만
-- 행 단위로 가릴 수 없어 unknown으로 표시하고, 사용자만 발생시키는 이벤트는 user로 둔다.
update notice_events
   set source = 'unknown'
 where event_type = 'impression';

create index if not exists search_logs_source_idx   on search_logs (source, created_at desc);
create index if not exists notice_events_source_idx on notice_events (source, created_at desc);

-- 실사용 지표 — 앞으로 숫자를 인용할 때는 이 뷰를 쓴다
create or replace view v_search_logs_daily_user as
  select date(created_at) as day,
         count(*) as searches,
         count(distinct ip_hash) as uniq_users,
         count(distinct matched_bizrno) as uniq_companies,
         sum(case when has_error or result_count = 0 then 1 else 0 end) as failed
  from search_logs
  where source = 'user'
  group by 1
  order by 1 desc;

create or replace view v_search_logs_top_queries_user as
  select query,
         count(*) as cnt,
         count(distinct ip_hash) as uniq_users,
         max(created_at) as last_seen
  from search_logs
  where source = 'user'
  group by query
  order by cnt desc;

-- 출처별 분포 — 내부 호출 비중이 다시 올라가면 계측이 깨졌다는 신호
create or replace view v_search_logs_sources as
  select date(created_at) as day, source, count(*) as cnt
  from search_logs
  group by 1, 2
  order by 1 desc, 3 desc;
