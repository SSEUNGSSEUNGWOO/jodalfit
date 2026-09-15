-- ====================================================================
-- 회사 사업자등록 상태 (국세청 진위확인·상태조회 API)
--
-- 회사 페이지 6만 개 중 폐업한 회사가 섞여 있다. 폐업 페이지는 검색 유입도 없고 얇은
-- 페이지로 색인 품질만 깎으므로 noindex 처리하고 사이트맵·업종 디렉토리에서 뺀다.
-- 적재: jobs/check_business_status.py (100건/호출, 일 100만 건 한도 — 전량 하루면 끝).
--
-- b_stt_cd: 01 계속사업자 / 02 휴업자 / 03 폐업자. 국세청 미등록 번호는 cd null + checked_at 만 기록.
-- ====================================================================

alter table companies
  add column if not exists biz_status_cd text,
  add column if not exists biz_status_nm text,
  add column if not exists biz_closed_dt date,
  add column if not exists biz_status_checked_at timestamptz;

-- 잡의 후보 선정(미조회 → 오래된 순)이 힙 전체를 훑지 않도록.
create index if not exists companies_biz_status_checked_idx
  on companies (biz_status_checked_at nulls first)
  where embedding is not null;

-- MV 는 정의를 바꿀 수 없어 지우고 다시 만든다. 사이트맵 라우트가 빈 창을 보지 않도록
-- 한 트랜잭션 안에서 drop → create → refresh 까지 마친다 (pg_cron 갱신 잡은 이름으로 참조하므로 그대로).
set statement_timeout = 0;
begin;

drop materialized view if exists industry_directory;
drop materialized view if exists industry_companies;
drop materialized view if exists sitemap_urls;

-- 0026 과 동일 + 폐업 제외
create materialized view sitemap_urls as
select
  'company'::text                                          as kind,
  (row_number() over (order by bizrno_norm) - 1)::int      as seq,
  '/companies/' || bizrno_norm                             as path,
  updated_at                                               as lastmod
from companies
where embedding is not null
  and bizrno_norm ~ '^\d{10}$'
  and coalesce(biz_status_cd, '') <> '03'
union all
select
  'notice',
  (row_number() over (order by n.bid_ntce_date desc, n.bid_ntce_no) - 1)::int,
  '/notices/' || n.bid_ntce_no,
  n.updated_at
from (
  select bid_ntce_no, bid_ntce_date, updated_at
  from (
    select distinct on (bid_ntce_no) bid_ntce_no, bid_ntce_date, updated_at
    from (
      select bid_ntce_no, bid_ntce_date, bid_ntce_ord, updated_at
      from bid_notices
      where bid_ntce_no is not null
      order by bid_ntce_date desc
      limit 15000
    ) r
    order by bid_ntce_no, bid_ntce_date desc, bid_ntce_ord desc
  ) d
  order by bid_ntce_date desc, bid_ntce_no
  limit 10000
) n
with no data;
create unique index sitemap_urls_kind_seq_idx on sitemap_urls (kind, seq);

-- 0027 과 동일 + 폐업 제외
create materialized view industry_companies as
with named as (
  select indstryty_cd, mode() within group (order by indstryty_nm) as indstryty_nm
  from company_industries
  where coalesce(indstryty_nm, '') <> ''
  group by indstryty_cd
)
select
  ci.indstryty_cd,
  n.indstryty_nm,
  (row_number() over (partition by ci.indstryty_cd order by c.bizrno_norm) - 1)::int as seq,
  c.bizrno,
  c.bizrno_norm,
  c.corp_nm,
  c.rgn_nm,
  c.corp_bsns_div_nm
from company_industries ci
join named n on n.indstryty_cd = ci.indstryty_cd
join companies c on c.bizrno = ci.bizrno
where c.embedding is not null
  and c.bizrno_norm ~ '^\d{10}$'
  and coalesce(c.biz_status_cd, '') <> '03'
  and coalesce(ci.indstryty_sttus_nm, '') <> '유효기간 경과'
with no data;
create unique index industry_companies_cd_seq_idx on industry_companies (indstryty_cd, seq);

create materialized view industry_directory as
select indstryty_cd, indstryty_nm, count(*)::int as company_count
from industry_companies
group by indstryty_cd, indstryty_nm
with no data;
create unique index industry_directory_cd_idx on industry_directory (indstryty_cd);

grant select on sitemap_urls, industry_companies, industry_directory to service_role;

refresh materialized view sitemap_urls;
refresh materialized view industry_companies;
refresh materialized view industry_directory;

commit;
