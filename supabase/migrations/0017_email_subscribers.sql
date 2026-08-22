-- ====================================================================
-- email_subscribers: 주간 공고 메일 웨이팅리스트
--
-- 발송 파이프라인은 아직 없다. 그런데 화면의 구독 폼이 입력을 아무 데도
-- 저장하지 않은 채 "구독 신청 완료"를 표시하고 있었다(EmailCaptureForm).
-- 최소한 신청을 실제로 받도록 만든 테이블이며, 발송 기능이 생기기 전까지는
-- "어느 회사 페이지에서 신청이 나오는가"라는 수요 신호로 쓴다.
-- ====================================================================

create table if not exists email_subscribers (
  id bigserial primary key,
  email text not null,
  bizrno_norm text,          -- 신청이 일어난 회사 페이지 (홈/기타면 null)
  created_at timestamptz default now()
);

-- 같은 이메일이 같은 회사 페이지에서 다시 눌러도 한 행만 남긴다.
-- (bizrno_norm이 null인 행끼리는 Postgres 규칙상 중복 허용 — 무해)
create unique index if not exists email_subscribers_email_bizrno_idx
  on email_subscribers (email, bizrno_norm);

create index if not exists email_subscribers_created_idx
  on email_subscribers (created_at desc);

-- service_role만 읽기/쓰기 (anon 차단). 정책을 두지 않아 anon은 전부 막힌다.
alter table email_subscribers enable row level security;

comment on table email_subscribers is
  '주간 메일 웨이팅리스트. 발송 파이프라인 미구축 상태이며 현재는 수요 측정용. 발송 시작 전까지 화면에 "발송 전" 문구를 유지할 것.';
