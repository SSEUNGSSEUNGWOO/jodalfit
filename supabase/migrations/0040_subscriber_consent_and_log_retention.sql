-- ====================================================================
-- 주간 메일 신청 동의 기록 + 이용 기록 1년 보관 후 삭제
--
-- /privacy (frontend/src/app/privacy/page.tsx, 시행 2026-09-22) 에 적은 대로 동작하게 한다.
--   · 신청 폼이 개인정보 수집·이용 / 광고성 정보 수신 동의를 받는다 → 동의 시각과 처리방침
--     버전(lib/privacy.ts 의 PRIVACY_VERSION)을 남긴다.
--   · 검색·이용 기록은 수집일로부터 1년이 지나면 삭제한다고 적었다 → 실제로 지운다.
--     두 테이블 모두 created_at 인덱스가 있어 오래된 행만 짚어 지운다.
--
-- 이 컬럼이 생기기 전에 들어온 신청(2026-09-22 기준 2건)은 동의 기록이 없다. 실제 발송을
-- 시작할 때 인증 메일로 동의를 다시 받는다.
-- ====================================================================

alter table email_subscribers
  add column if not exists consented_at timestamptz,
  add column if not exists consent_version text;

comment on column email_subscribers.consented_at is
  '개인정보 수집·이용 + 광고성 정보 수신 동의 시각. null 이면 동의 기록 없음(0040 이전 신청).';
comment on column email_subscribers.consent_version is
  '동의 당시 개인정보처리방침 시행일 (frontend lib/privacy.ts PRIVACY_VERSION).';

-- 매주 일요일 KST 04:00 (UTC 토 19:00) — 수집 잡·MV 갱신과 겹치지 않는 시간.
select cron.schedule(
  'purge-logs-older-than-1y',
  '0 19 * * 6',
  $$set statement_timeout = 0;
    delete from search_logs   where created_at < now() - interval '1 year';
    delete from notice_events where created_at < now() - interval '1 year';$$
);
