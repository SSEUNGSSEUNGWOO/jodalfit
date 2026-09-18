-- marketing_daily_stats(0033)를 search_logs.source(0034) 기준으로 교체.
-- 0033은 user_agent 'node%'만 빼서 크롤러(bot)가 "사람 검색"에 섞여 있었다.
-- source 로 사람(user) / 내부 SSR(internal) / 봇(bot)을 나누고, 봇 수도 따로 돌려준다.
-- notice_events 는 0034 이후 사용자 이벤트만 적재되지만 과거 행 호환을 위해 source='user' 로 거른다.

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
  day_logs as (
    select s.* from search_logs s, bounds b
    where s.created_at >= b.d0 and s.created_at < b.d1
  ),
  human as (select * from day_logs where source = 'user'),
  prev_week_companies as (
    select distinct s.matched_bizrno from search_logs s, bounds b
    where s.created_at >= b.w0 and s.created_at < b.d0
      and s.source = 'user'
      and s.matched_bizrno is not null
  ),
  today_companies as (
    select distinct matched_bizrno from human where matched_bizrno is not null
  ),
  ev as (
    select e.event_type, count(*)::int as n from notice_events e, bounds b
    where e.created_at >= b.d0 and e.created_at < b.d1
      and e.source = 'user'
      and e.event_type in ('click', 'save', 'dismiss', 'subscribe')
    group by e.event_type
  )
  select jsonb_build_object(
    'date', p_date,
    'human_searches', (select count(*) from human),
    'unique_users', (select count(distinct ip_hash) from human),
    'ssr_searches', (select count(*) from day_logs where source = 'internal'),
    'bot_searches', (select count(*) from day_logs where source = 'bot'),
    'company_mode_searches', (select count(*) from human where mode = 'company'),
    'company_identified', (select count(*) from human where mode = 'company' and matched_bizrno is not null),
    'errors', (select count(*) from human where has_error),
    'error_top', (select coalesce(jsonb_agg(jsonb_build_object('msg', msg, 'n', n) order by n desc), '[]'::jsonb)
                    from (select left(error_msg, 60) as msg, count(*)::int as n from human
                          where has_error group by 1 order by 2 desc limit 3) t),
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
