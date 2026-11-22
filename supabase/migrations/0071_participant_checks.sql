-- supabase/migrations/0071_participant_checks.sql
-- 참가업체를 조회했지만 rank 2+ 가 없던 공고(단독 응찰 등)를 적어 두는 표.
--
-- ingest_bid_participants 는 "이미 받은 공고"를 award_results 의 rank 2 행으로 판정한다. 입찰자가 한 곳뿐인 공고는
-- 그 행이 영영 안 생겨 수집 창(2일) 안에서 매일 다시 조회됐다 — 2026-11-20 실측: 전부 받은 직후에도 대기열 539건 중
-- 216건이 남았다. 참가업체 API 는 하루 호출 한도가 1,000회 안팎이라(같은 날 LIMITED_NUMBER_OF_SERVICE_REQUESTS 로 확인)
-- 결과 없는 조회가 한도의 5분의 1을 먹었다.
--
-- 잡은 이 표가 없어도 돈다(조회·기록 모두 try/except — 예전처럼 다시 조회할 뿐). 되돌리기 = drop table participant_checks.
-- 0062 로 public 기본 권한에서 anon/authenticated 가 빠져 있어 따로 열지 않는다(service_role 만 쓴다).
-- Dashboard SQL Editor 또는 psycopg 로 실행.

create table if not exists participant_checks (
  bid_ntce_no text primary key,
  checked_at timestamptz not null default now()
);

alter table participant_checks enable row level security;
