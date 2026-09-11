-- ====================================================================
-- 업종별 기업 디렉토리 (materialized view)
--
-- GSC 데이터(2026-09): 순수 회사명 검색은 잡코리아·사람인·크레탑이 상단을 차지해 CTR 2%대인
-- 반면 "지역+회사명", 소규모 업체 같은 롱테일은 CTR 40~100%. 회사명 단독 페이지 6만 개보다
-- "○○공사업 등록 업체" 같은 집계 페이지가 조달핏이 1등 할 수 있는 자리다.
--
-- company_industries(15만 행) × companies(16만 행) 조인을 매 요청 돌리지 않도록 하루 한 번 고정.
-- 라우트는 (indstryty_cd, seq) 창(window)만 읽는다 — sitemap_urls(0026)와 같은 패턴.
--
-- 업종명: 같은 코드에 이름이 비어 오는 행이 섞여 있어(폐지·구 코드 추정) 코드별 최빈 비어있지
-- 않은 이름을 대표명으로 쓴다. 이름이 전혀 없는 코드(352개)는 페이지 제목을 만들 수 없어 제외.
-- ====================================================================

create materialized view if not exists industry_companies as
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
  and coalesce(ci.indstryty_sttus_nm, '') <> '유효기간 경과'
with no data;

create unique index if not exists industry_companies_cd_seq_idx on industry_companies (indstryty_cd, seq);

-- 업종 목록 + 업체 수. 디렉토리 인덱스 페이지와 사이트맵이 읽는다.
create materialized view if not exists industry_directory as
select indstryty_cd, indstryty_nm, count(*)::int as company_count
from industry_companies
group by indstryty_cd, indstryty_nm
with no data;

create unique index if not exists industry_directory_cd_idx on industry_directory (indstryty_cd);

grant select on industry_companies, industry_directory to service_role;

-- 최초 적재. Disk IO 소진 상태에선 기본 statement_timeout(2분)을 넘길 수 있어 세션에서 푼다.
set statement_timeout = 0;
refresh materialized view industry_companies;
refresh materialized view industry_directory;

-- 매일 08:10 KST (23:10 UTC) — sitemap_urls 갱신(23:00) 직후, 회사 기본정보 백필·업종 풍부화 반영.
-- industry_directory 는 industry_companies 에서 파생되므로 순서대로 한 명령에서 돌린다.
select cron.schedule(
  'refresh-industry-directory',
  '10 23 * * *',
  $$set statement_timeout = 0; refresh materialized view concurrently industry_companies; refresh materialized view concurrently industry_directory$$
);
