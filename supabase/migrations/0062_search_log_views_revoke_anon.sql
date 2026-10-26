-- 0062: search_logs 뷰를 anon/authenticated 에서 거둔다 (2026-10-26 보안 점검)
--
-- search_logs 표 자체는 RLS 가 켜져 있어 anon 키로 못 읽지만, 그 위의 뷰(0008·0034)는 기본
-- security_invoker=off 라 뷰 소유자(postgres) 권한으로 돌아 RLS 를 우회했다. 운영 번들에 들어 있는
-- 공개 anon 키로 v_search_logs_recent(검색어·매칭 회사명·ip_hash·referer)·top_queries 가 그대로
-- 읽혔다. 이 뷰들은 /admin(service_role)·marketing_report(service_role)만 쓴다.
--
-- 되돌리기: grant select on <view> to anon, authenticated;

revoke all on public.v_search_logs_recent            from anon, authenticated;
revoke all on public.v_search_logs_top_queries       from anon, authenticated;
revoke all on public.v_search_logs_failed            from anon, authenticated;
revoke all on public.v_search_logs_daily             from anon, authenticated;
revoke all on public.v_search_logs_modes             from anon, authenticated;
revoke all on public.v_search_logs_daily_user        from anon, authenticated;
revoke all on public.v_search_logs_top_queries_user  from anon, authenticated;
revoke all on public.v_search_logs_sources           from anon, authenticated;

-- 앞으로 만드는 뷰도 anon 에 자동 부여되지 않게 — public 스키마의 기본 권한에서 anon/authenticated 를 뺀다.
-- (표는 rls_auto_enable 이벤트 트리거가 RLS 를 켜 주지만 뷰는 RLS 가 없다.)
alter default privileges in schema public revoke all on tables from anon, authenticated;
