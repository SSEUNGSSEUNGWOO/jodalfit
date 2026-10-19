-- ====================================================================
-- 0052 user_consents — 가입 때 받은 동의 기록 (이용약관·개인정보 필수, 알림 메일 선택)
--
-- 가입 폼은 동의를 auth.signUp 의 user_metadata 로 보낸다(확인 전엔 세션이 없어 RLS 테이블에 직접 못 쓴다).
-- auth.users 에 행이 생길 때 트리거가 metadata 를 이 표로 옮긴다. consented_at 은 metadata 를 신뢰하지 않고
-- 트리거 실행 시각(서버 시각)을 찍는다 — 서버 시각이 기록의 진실값. 이후 metadata 가 바뀌어도 이 표는 그대로 —
-- "가입 당시 무엇에 동의했나"가 기록의 뜻이다. 알림 수신 변경은 나중 설정 페이지가 update 한다(별도 정책).
-- Dashboard SQL Editor 에서 실행 (CLI 아님).
-- ====================================================================

create table if not exists public.user_consents (
  user_id          uuid primary key references auth.users(id) on delete cascade,
  terms_version    text not null,
  privacy_version  text not null,
  marketing_opt_in boolean not null default false,
  consented_at     timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

comment on table public.user_consents is '가입 시 동의 기록. terms_version=lib/terms.ts TERMS_VERSION, privacy_version=lib/privacy.ts PRIVACY_VERSION.';

alter table public.user_consents enable row level security;

grant select, update (marketing_opt_in) on public.user_consents to authenticated;

drop policy if exists "own consent read" on public.user_consents;
create policy "own consent read" on public.user_consents
  for select using (auth.uid() = user_id);

drop policy if exists "own marketing_opt_in update" on public.user_consents;
create policy "own marketing_opt_in update" on public.user_consents
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create or replace function public.handle_new_user_consent()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_consents (user_id, terms_version, privacy_version, marketing_opt_in, consented_at)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'terms_version', ''),
    coalesce(new.raw_user_meta_data->>'privacy_version', ''),
    coalesce(nullif(new.raw_user_meta_data->>'marketing_opt_in', '') ~* '^(true|t|1)$', false),
    now()
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_consent on auth.users;
create trigger on_auth_user_created_consent
  after insert on auth.users
  for each row execute function public.handle_new_user_consent();

-- 동의 기록은 불변 — 설정 페이지가 바꿀 수 있는 것은 marketing_opt_in 뿐. updated_at 은 여기서 찍는다(0001 의 set_updated_at 관례).
create or replace function public.lock_consent_history()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.user_id <> old.user_id
     or new.terms_version <> old.terms_version
     or new.privacy_version <> old.privacy_version
     or new.consented_at <> old.consented_at then
    raise exception 'user_consents: user_id/terms_version/privacy_version/consented_at are immutable';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_user_consents_lock_history on public.user_consents;
create trigger trg_user_consents_lock_history
  before update on public.user_consents
  for each row execute function public.lock_consent_history();
