-- supabase/migrations/0064_consent_first_fill.sql
-- ====================================================================
-- 0064 소셜 로그인(구글 OAuth, 2026-10-28)의 동의 기록 — 빈 동의 행은 한 번 채울 수 있게
--
-- 0052 트리거는 auth.users insert 때 raw_user_meta_data 의 terms_version/privacy_version 으로 user_consents 를 만든다.
-- 이메일 가입은 가입 폼이 그 메타데이터를 넘기지만, OAuth(signInWithOAuth)는 메타데이터를 못 넘기므로 행이 ''/'' 로 생긴다.
-- 그래서 첫 로그인 뒤 /consent 한 판에서 받은 동의를 service_role 이 UPDATE 로 채운다.
-- 불변 규칙은 그대로다 — terms_version/privacy_version 이 '' 인 행(아직 동의 안 받음)만 한 번 채워지고, 채워진 뒤엔 0052 와 같이 잠긴다.
-- 되돌리기: 0052 의 lock_consent_history 를 다시 실행.
-- ====================================================================

create or replace function public.lock_consent_history()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  first_fill boolean := old.terms_version = '' and old.privacy_version = '' and new.terms_version <> '' and new.privacy_version <> '';
begin
  if new.user_id <> old.user_id then
    raise exception 'user_consents: user_id is immutable';
  end if;
  if not first_fill and (
       new.terms_version <> old.terms_version
    or new.privacy_version <> old.privacy_version
    or new.consented_at <> old.consented_at) then
    raise exception 'user_consents: user_id/terms_version/privacy_version/consented_at are immutable';
  end if;
  new.updated_at := now();
  return new;
end;
$$;
