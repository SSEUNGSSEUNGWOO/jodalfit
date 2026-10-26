-- supabase/migrations/0061_feedback.sql
-- ====================================================================
-- 0061 feedback — 사이트 "의견 보내기"(/feedback) 가 남기는 의견·문의·오류 제보 (2026-10-26)
--
-- 쓰기는 백엔드 POST /feedback(service_role) 만, 읽기는 /admin(service_role) 만. RLS 를 켜고 정책을 두지 않아
-- anon·세션 클라이언트는 어느 쪽도 못 한다. 가입 없이 보낼 수 있으므로 user_id 는 두지 않는다 — 답장용 email 만(선택).
-- handled_at 은 운영자가 처리한 시각(지금은 대시보드에서 손으로). Dashboard SQL Editor 에서 실행 (CLI 아님).
-- ====================================================================

create table if not exists public.feedback (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  kind        text not null check (kind in ('idea', 'question', 'bug')),
  message     text not null check (length(message) between 5 and 2000),
  email       text check (email is null or length(email) <= 200),
  page        text check (page is null or length(page) <= 500),
  ip_hash     text,
  user_agent  text check (user_agent is null or length(user_agent) <= 500),
  handled_at  timestamptz
);
comment on table public.feedback is '/feedback 폼의 의견(idea)·문의(question)·오류 제보(bug). page = 폼을 연 직전 페이지(referrer).';

create index if not exists feedback_created_at_idx on public.feedback (created_at desc);

alter table public.feedback enable row level security;   -- 정책 없음 = service_role 만
