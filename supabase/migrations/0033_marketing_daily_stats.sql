-- 일일 마케팅 성적표(jobs/marketing_report)의 "사람 행동"·"제품 건강" 칸을 한 번의 RPC 로 집계.
-- 하루 경계는 KST. SSR(회사 페이지 → 백엔드) 호출은 user_agent 가 'node' 라 사람 검색에서 뺀다.
-- 재검색율 = 그날 사람이 검색한 회사 중, 직전 7일 안에도 사람이 검색했던 회사의 비율 (브리프의 "재검색 정착").

create index if not exists notice_events_created_idx on notice_events (created_at);

create or replace function marketing_daily_stats(p_date date)
returns jsonb
language sql
stable
as $$
  with bounds as (
    select (p_date::timestamp at time zone 'Asia/Seoul') as d0,
           ((p_date + 1)::timestamp at time zone 'Asia/Seoul') as d1,
           ((p_date - 7)::timestamp at time zone 'Asia/Seoul') as w0
  ),
  human as (
    select s.* from search_logs s, bounds b
    where s.created_at >= b.d0 and s.created_at < b.d1
      and coalesce(s.user_agent, '') not like 'node%'
  ),
  prev_week_companies as (
    select distinct s.matched_bizrno from search_logs s, bounds b
    where s.created_at >= b.w0 and s.created_at < b.d0
      and coalesce(s.user_agent, '') not like 'node%'
      and s.matched_bizrno is not null
  ),
  today_companies as (
    select distinct matched_bizrno from human where matched_bizrno is not null
  ),
  ev as (
    select e.event_type, count(*)::int as n from notice_events e, bounds b
    where e.created_at >= b.d0 and e.created_at < b.d1
      and e.event_type in ('click', 'save', 'dismiss', 'subscribe')
    group by e.event_type
  )
  select jsonb_build_object(
    'date', p_date,
    'human_searches', (select count(*) from human),
    'ssr_searches', (select count(*) from search_logs s, bounds b
                      where s.created_at >= b.d0 and s.created_at < b.d1 and coalesce(s.user_agent, '') like 'node%'),
    'company_mode_searches', (select count(*) from human where mode = 'company'),
    'company_identified', (select count(*) from human where mode = 'company' and matched_bizrno is not null),
    'errors', (select count(*) from human where has_error),
    'zero_results', (select count(*) from human where not has_error and coalesce(result_count, 0) = 0 and coalesce(kw_result_count, 0) = 0),
    'p50_latency_ms', (select percentile_cont(0.5) within group (order by latency_ms) from human where latency_ms is not null),
    'unique_companies', (select count(*) from today_companies),
    'returning_companies', (select count(*) from today_companies t where exists (select 1 from prev_week_companies p where p.matched_bizrno = t.matched_bizrno)),
    'events', (select coalesce(jsonb_object_agg(event_type, n), '{}'::jsonb) from ev),
    'subscribers_new', (select count(*) from subscribers s, bounds b where s.created_at >= b.d0 and s.created_at < b.d1),
    'subscribers_verified', (select count(*) from subscribers s, bounds b where s.verified_at >= b.d0 and s.verified_at < b.d1),
    'email_subscribers_new', (select count(*) from email_subscribers s, bounds b where s.created_at >= b.d0 and s.created_at < b.d1)
  );
$$;
