-- ====================================================================
-- 사이트맵 lastmod 를 "수집 시각"에서 "내용 변경 시각"으로 바꾼다
--
-- 0026 은 lastmod 에 소스 테이블의 updated_at 을 그대로 썼다. 그런데 일일 수집 잡이
-- 매일 회사·공고 행을 upsert 하므로(ingest_contracts 가 10-06 에 신규 회사 23,123개,
-- backfill_companies_basic 하루 3,000개, ingest_company_details 1,500개) 페이지에
-- 보이는 내용이 그대로여도 updated_at 은 올라간다. 결과:
--   2026-10-10 실측 — company URL 75,291개 중 57,619개(76.5%)가 "최근 7일 안에 변경"
--   이라고 주장하고, 그게 매일 반복됐다. sitemap/0.xml 의 10,000개 lastmod 는 고유값이
--   297개뿐이고 전부 전날 생성 시각대에 몰려 있었다.
-- 구글은 lastmod 가 신뢰 불가라고 판단하면 무시한다 — 7만 URL 중 무엇을 다시 볼지에
-- 대한 신호가 0이 된다. frontend/src/app/sitemap.ts:15-17 이 이 위험을 적어두고
-- STATIC_LASTMOD 를 두었지만, 가드가 폴백 경로만 덮어 DB 값이 있으면 그대로 나갔다.
--
-- 그래서 각 페이지의 내용을 실제로 만드는 값으로 바꾼다.
--   · 회사 페이지(제목이 "<상호> 나라장터 수주 이력")  → 마지막 수주일
--     = max(contracts.cntrct_cncls_date). 새로 수주할 때만 움직인다. 수주 이력이 없는
--     회사는 null 로 두면 sitemap.ts 가 STATIC_LASTMOD 로 폴백한다 (실측 1,304개).
--   · 공고 라이프사이클 페이지 → 공고일(bid_ntce_date). 공고별로 고정이고, 이 세그먼트는
--     애초에 최신 10,000건만 실으므로 전부 최근 날짜다.
-- 적용 후 실측: 최근 7일 집중이 76.5% → 16.1% (남은 16%는 실제로 최근 수주한 회사).
-- lastmod 타입이 timestamptz → date 로 바뀐다. 읽는 쪽(lib/sitemap-urls.ts)이
-- `lastmod: string | null` 이라 프론트 변경은 없다.
--
-- 교체는 원자적으로 한다. 0026 처럼 `with no data` 로 만들고 나중에 refresh 하면 그 사이
-- MV 가 "존재하는데 0행" 상태가 되고, fetchSitemapUrls 는 그걸 오류가 아니라 빈 배열로
-- 받아 빈 200 사이트맵을 내보낸다 — 2026-07~09 에 구글 색인을 끊은 바로 그 실패다.
-- 새 이름으로 데이터까지 채워 만든 뒤 트랜잭션 안에서 이름만 바꾼다.
-- ====================================================================

-- 회사 75,538행 집계에 실측 27초. DB 기본 statement_timeout(2분)으로도 되지만
-- Disk IO 소진 상태를 대비해 푼다 (0026 과 같은 이유).
set statement_timeout = 0;

create materialized view sitemap_urls_next as
select
  'company'::text                                            as kind,
  (row_number() over (order by c.bizrno_norm) - 1)::int       as seq,
  '/companies/' || c.bizrno_norm                             as path,
  w.last_win                                                 as lastmod
from companies c
left join (
  select rprsnt_corp_bizrno_norm as b, max(cntrct_cncls_date) as last_win
  from contracts
  where rprsnt_corp_bizrno_norm is not null
    and cntrct_cncls_date is not null
  group by 1
) w on w.b = c.bizrno_norm
where c.embedding is not null
  and c.bizrno_norm ~ '^\d{10}$'
union all
select
  'notice',
  (row_number() over (order by n.bid_ntce_date desc, n.bid_ntce_no) - 1)::int,
  '/notices/' || n.bid_ntce_no,
  n.bid_ntce_date
from (
  -- 0026 과 같은 행 선택 로직. 같은 공고가 차수(bid_ntce_ord)별로 여러 행이라
  -- 공고번호당 최신 1행만. 33만 행 전체를 정렬하지 않도록 bid_ntce_date 인덱스로
  -- 최신 15,000행만 뜬 뒤 중복 제거 (중복률 약 12% → 10,000개는 남는다).
  select bid_ntce_no, bid_ntce_date
  from (
    select distinct on (bid_ntce_no) bid_ntce_no, bid_ntce_date
    from (
      select bid_ntce_no, bid_ntce_date, bid_ntce_ord
      from bid_notices
      where bid_ntce_no is not null
      order by bid_ntce_date desc
      limit 15000
    ) r
    order by bid_ntce_no, bid_ntce_date desc, bid_ntce_ord desc
  ) d
  order by bid_ntce_date desc, bid_ntce_no
  limit 10000
) n;

-- refresh ... concurrently 에 유니크 인덱스가 필요하고, 라우트 조회도 이 인덱스를 탄다.
create unique index sitemap_urls_next_kind_seq_idx on sitemap_urls_next (kind, seq);

-- 원자적 교체 — 빈 200 창(window)을 만들지 않는다.
begin;
drop materialized view sitemap_urls;
alter materialized view sitemap_urls_next rename to sitemap_urls;
alter index sitemap_urls_next_kind_seq_idx rename to sitemap_urls_kind_seq_idx;
commit;

-- 새 MV 에는 Supabase 기본 권한이 다시 붙는다 — 0041 대로 공개 키 접근을 회수한다.
grant select on sitemap_urls to service_role;
revoke select on sitemap_urls from anon, authenticated;

-- pg_cron 작업 'refresh-sitemap-urls'(0026, 매일 23:00 UTC)는 명령 텍스트에서
-- 이름으로 참조하므로 rename 후에도 그대로 동작한다 — 재등록하지 않는다.
