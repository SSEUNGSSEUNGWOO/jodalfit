-- supabase/migrations/0054_saved.sql
-- ====================================================================
-- 0054 saved_companies · reviewed_notices — 저장한 회사(☆)와 검토 표시한 공고 (리뉴얼 03)
--
-- 브라우저가 anon 키 + 세션 쿠키로 직접 insert/delete 한다. user_id 는 기본값 auth.uid() — 클라이언트는
-- user_id 를 보내지 않는다. 정책은 전부 auth.uid() = user_id. update 는 없다(토글은 insert/delete).
-- reviewed_notices.why 는 검토를 누른 순간의 근거 칩 한 개(예: "재출현 기관") — 검토함 둘째 줄에 그대로 보여 준다.
-- 마감 30일 지난 검토 행은 pg_cron 이 주 1회 지운다(시안 문구 "마감 30일 뒤 자동 정리"). (공고 행이 없거나 마감일이 없는 검토 행은 1년 뒤)
-- Dashboard SQL Editor 에서 실행 (CLI 아님).
-- ====================================================================

create table if not exists public.saved_companies (
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  bizrno_norm text not null check (bizrno_norm ~ '^\d{10}$'),
  created_at  timestamptz not null default now(),
  primary key (user_id, bizrno_norm)
);
comment on table public.saved_companies is '사용자가 ☆ 로 저장한 회사. bizrno_norm = companies.bizrno_norm (10자리).';

create table if not exists public.reviewed_notices (
  user_id         uuid not null default auth.uid() references auth.users(id) on delete cascade,
  bid_ntce_no     text not null,
  bid_ntce_ord    text not null default '000',
  via_bizrno_norm text check (via_bizrno_norm is null or via_bizrno_norm ~ '^\d{10}$'),
  -- why 의 인라인 check 는 새로 만드는 환경용 — 테이블이 이미 있는 환경에서는 create table if not exists 가 반영하지 않으므로
  -- 아래 alter table 두 줄(멱등)로 따로 붙인다.
  why             text check (why is null or length(why) <= 60),
  created_at      timestamptz not null default now(),
  primary key (user_id, bid_ntce_no, bid_ntce_ord)
);
comment on table public.reviewed_notices is '사용자가 검토 표시한 공고. via_bizrno_norm = 어느 회사 결과에서 검토했는지. why = 그때의 근거 칩.';

-- 이미 만들어진 환경(테이블이 위 create table if not exists 를 건너뛴 경우)에도 why 길이 제한을 붙인다.
alter table public.reviewed_notices drop constraint if exists reviewed_notices_why_check;
alter table public.reviewed_notices add constraint reviewed_notices_why_check check (why is null or length(why) <= 60);

alter table public.saved_companies  enable row level security;
alter table public.reviewed_notices enable row level security;

grant select, insert, delete on public.saved_companies  to authenticated;
grant select, insert, delete on public.reviewed_notices to authenticated;

-- anon 은 이 표에 올 일이 없다(비로그인은 로그인 링크). 서버 읽기는 세션 없으면 권한 오류를 빈 값으로 처리한다(lib/saved.ts).
revoke all on public.saved_companies, public.reviewed_notices from anon;

-- Supabase 스키마 기본 권한(pg_default_acl)이 anon·authenticated 에 7종(arwdDxtm)을 전부 붙인다 — 0041 주석과 같은 사정.
-- RLS 가 막지 못하는 TRUNCATE 와, 위 주석대로 존재하지 않아야 하는 UPDATE 를 회수한다. select/insert/delete 는 RLS 가 행 단위로 거른다.
revoke truncate, references, trigger, update on public.saved_companies, public.reviewed_notices from anon, authenticated;

drop policy if exists "own saved_companies" on public.saved_companies;
create policy "own saved_companies" on public.saved_companies
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own reviewed_notices" on public.reviewed_notices;
create policy "own reviewed_notices" on public.reviewed_notices
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 마감 30일 지난 검토 행 삭제 — 매주 토요일 19:00 UTC(KST 일 04:00, 0040 의 로그 정리와 같은 시각대).
-- cron 세션에도 2분 statement_timeout 이 걸리므로 첫 문장은 항상 set statement_timeout = 0 (0026 관례).
select cron.unschedule(jobid) from cron.job where jobname = 'purge-reviewed-notices-expired';
select cron.schedule('purge-reviewed-notices-expired', '0 19 * * 6', $$
  set statement_timeout = 0;
  delete from public.reviewed_notices r
   where r.created_at < now() - interval '1 year'
      or exists (select 1 from public.bid_notices n
                  where n.bid_ntce_no = r.bid_ntce_no and n.bid_ntce_ord = r.bid_ntce_ord
                    and n.bid_clse_date < current_date - 30);
$$);
