-- search_logs 분석용 view 모음.
-- Supabase Dashboard → Table Editor 좌측 메뉴에서 "v_..." 클릭하면 바로 조회.

-- 최근 검색 (created_at desc, 컬럼만 정리)
create or replace view v_search_logs_recent as
  select created_at, mode, query, matched_corp_nm, result_count, kw_result_count,
         has_error, error_msg, latency_ms, ip_hash, referer
  from search_logs
  order by created_at desc;

-- 검색어 TOP — 가장 많이 검색된 query (회사명/키워드)
create or replace view v_search_logs_top_queries as
  select query,
         count(*) as cnt,
         count(distinct ip_hash) as uniq_users,
         max(created_at) as last_seen
  from search_logs
  group by query
  order by cnt desc;

-- 매칭 실패 — 회사 인식 안 됨 또는 결과 0건
create or replace view v_search_logs_failed as
  select created_at, query, mode, has_error, error_msg, result_count
  from search_logs
  where has_error or result_count = 0
  order by created_at desc;

-- 일자별 검색량 + 순방문
create or replace view v_search_logs_daily as
  select date(created_at) as day,
         count(*) as searches,
         count(distinct ip_hash) as uniq_users,
         sum(case when has_error or result_count = 0 then 1 else 0 end) as failed
  from search_logs
  group by 1
  order by 1 desc;

-- 모드별 분포 (company / keywords / auto)
create or replace view v_search_logs_modes as
  select mode, count(*) as cnt
  from search_logs
  group by mode
  order by cnt desc;
