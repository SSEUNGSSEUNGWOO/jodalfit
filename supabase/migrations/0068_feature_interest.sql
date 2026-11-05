-- ====================================================================
-- 0068 기능 관심 등록 — 공고 상세의 "제안서 작성 준비안 관심 등록" (2026-11-05)
--
-- 아직 만들지 않은 기능의 수요를 공고 화면에서 직접 묻는다. 약속 없이 "검토하고 있다 · 필요하면 관심 등록" 만 보여 주고,
-- 누른 사람·공고를 기록한다. /admin "제안서 작성 준비안 관심" 판이 읽는다. feature='proposal_prep'
-- (제안요청서 기준 목차·평가항목 대응표·준비 자료 목록 — 회사 맞춤 "초안"은 회사만 아는 자료가 필요해 첫 단계가 아니다).
--   event='view'     : 버튼이 실제 화면에 들어온 때(브라우저 IntersectionObserver, 공고·탭당 1회) — 클릭률의 분모.
--                      공고 페이지 렌더링의 97% 가 크롤러라 서버 렌더 수를 분모로 쓰면 안 된다(2026-11-05).
--   event='register' : 클릭. 로그인 사용자는 (feature, 공고, user_id) 로 한 번만, 비로그인은 user_id null 로 따로 센다 —
--                      가입 과정에서 이탈한 관심을 놓치지 않기 위해.
-- 쓰기는 frontend /api/interest(service_role). 0062 로 anon/authenticated 기본 권한이 없으니 RLS 만 켜고 정책 없음.
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 새 표라 psycopg 로 직접 넣어도 된다(drop 으로 되돌림).
-- ====================================================================

create table if not exists public.feature_interest (
  id           bigint generated always as identity primary key,
  created_at   timestamptz not null default now(),
  feature      text not null default 'proposal_prep' check (length(feature) between 1 and 40),
  event        text not null check (event in ('view', 'register')),
  bid_ntce_no  text not null check (length(bid_ntce_no) between 5 and 30),
  bid_ntce_ord text,
  user_id      uuid references auth.users(id) on delete set null,
  session_id   text check (session_id is null or length(session_id) <= 64),
  user_agent   text check (user_agent is null or length(user_agent) <= 300)
);
comment on table public.feature_interest is '미출시 기능 수요 조사 — view(버튼 노출)/register(관심 등록). 분모는 view, 봇 UA 는 쓰지 않는다.';
create index if not exists feature_interest_created_idx on public.feature_interest (created_at desc);
create unique index if not exists feature_interest_register_user_uidx
  on public.feature_interest (feature, bid_ntce_no, user_id) where event = 'register' and user_id is not null;
alter table public.feature_interest enable row level security;
