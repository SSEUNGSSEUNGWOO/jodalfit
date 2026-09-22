-- ====================================================================
-- MV 를 공개 키(anon/authenticated)로 읽지 못하게 한다
--
-- 테이블은 전부 RLS 가 켜져 있고 정책이 없어 anon 으로는 한 행도 못 읽는다. 그런데 MV 에는
-- RLS 가 없고, Supabase 기본 권한 때문에 anon·authenticated 에 SELECT 가 붙어 있었다
-- (2026-09-22 확인). 공개 키만 있으면 REST 로 그대로 읽힌다 —
--   · industry_companies: 회사 12만 7천 곳의 마스킹 안 된 사업자번호·상호. 비공개 요청 회사도
--     남아 있다(0037 에서 MV 재생성을 못 해 앱 쪽에서만 걸렀다).
--   · institution_repeat_stats_cached 처럼 MV 를 읽는 SECURITY INVOKER 함수도 같은 이유로 열려 있었다.
-- 앱은 DB 에 전부 service_role 로 접근하고 공개 키는 코드·클라이언트 번들 어디에도 없다(같은 날 확인).
-- 그래서 회수해도 잃는 것이 없다.
--
-- 새 MV 를 만들 때마다 기본 권한이 다시 붙는다 — 만들고 나서 아래처럼 회수할 것.
-- ====================================================================

revoke select on sitemap_urls                from anon, authenticated;
revoke select on industry_companies          from anon, authenticated;
revoke select on industry_directory          from anon, authenticated;
revoke select on institution_repeat_stats_mv from anon, authenticated;
revoke select on institution_bid_rate_mv     from anon, authenticated;
