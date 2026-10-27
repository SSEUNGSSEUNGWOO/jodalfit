-- ====================================================================
-- 0063 결과 화면 "도움이 됐습니까" 응답 + 주간 메일 발송 기록 (2026-10-27)
--
-- result_feedback  : 결과 화면 맨 아래 한 줄 — 예/아니오 + (아니오면) 한 줄 메모. 추천 품질을 사용자 쪽에서 재는 유일한 수단.
--                    백엔드 POST /events/helpful 이 service_role 로 넣는다. /admin 응답 건강 판이 읽는다.
-- weekly_mail_log  : jobs/send_weekly_mail 이 보낸 메일 한 통 = 한 행. 같은 주 재실행 때 두 번 보내지 않는 기준.
--
-- 수신 대상은 새 표가 아니라 0052 user_consents.marketing_opt_in(가입 때 "[선택] 알림 메일 수신 동의")이다.
-- 메일 하단 "그만 받기" 와 검토함의 토글이 그 열을 바꾼다(0052 의 lock 트리거가 허용하는 유일한 열).
--
-- 0062 가 public 기본 권한에서 anon/authenticated 를 뺐으므로 두 표는 service_role 만 읽고 쓴다. RLS 는 켜 두되 정책 없음.
-- Dashboard SQL Editor 에서 실행 (CLI 아님). psycopg 로 직접 넣어도 된다(새 표 — drop 으로 되돌릴 수 있다).
-- ====================================================================

create table if not exists public.result_feedback (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  mode        text not null check (mode in ('company', 'keywords')),
  query       text not null check (length(query) between 1 and 200),
  bizrno_norm text check (bizrno_norm is null or bizrno_norm ~ '^\d{10}$'),
  helpful     boolean not null,
  note        text check (note is null or length(note) <= 300),
  session_id  text check (session_id is null or length(session_id) <= 64),
  source      text not null default 'user'   -- app/core/traffic_source.py 의 라벨(user/internal/bot)
);
comment on table public.result_feedback is '결과 화면 "이 결과가 검토에 도움이 됐습니까?" 응답. 숫자를 인용할 때는 source=user 만.';
create index if not exists result_feedback_created_idx on public.result_feedback (created_at desc);
alter table public.result_feedback enable row level security;

create table if not exists public.weekly_mail_log (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  sent_at    timestamptz not null default now(),
  companies  int not null,
  notices    int not null,
  resend_id  text
);
comment on table public.weekly_mail_log is 'jobs/send_weekly_mail 발송 기록. 같은 사용자에게 6일 안에 또 보내지 않는다.';
create index if not exists weekly_mail_log_user_sent_idx on public.weekly_mail_log (user_id, sent_at desc);
alter table public.weekly_mail_log enable row level security;
