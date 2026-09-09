-- 사이트맵이 매 요청 companies 힙 6만 행을 훑고(embedding is not null 필터는 힙 접근 필요)
-- Disk IO 예산 소진 상태에선 페이지당 40초를 넘겨 PostgREST 오류가 났다. 코드가 그 오류를
-- 삼켜 빈 200을 내보낸 탓에 2026-09 기준 세그먼트 1~5가 URL 0개로 서빙됐고, 구글은
-- 7월 이후 깊은 페이지를 다시 크롤하지 않았다 (색인 상태 "크롤링됨 - 색인 안 됨").
--
-- 사이트맵 대상 URL을 하루 한 번 materialized view 로 고정한다. 라우트는 (kind, seq)
-- 인덱스로 창(window)만 읽으므로 DB 부하와 무관하게 ms 단위로 응답한다.
-- 세그먼트 번호·크기는 frontend/src/lib/sitemap-segments.ts 가 결정하고, 여기선
-- kind 별 연번(seq)만 매긴다.

create materialized view if not exists sitemap_urls as
select
  'company'::text                                          as kind,
  (row_number() over (order by bizrno_norm) - 1)::int      as seq,
  '/companies/' || bizrno_norm                             as path,
  updated_at                                               as lastmod
from companies
where embedding is not null
  and bizrno_norm ~ '^\d{10}$'
union all
select
  'notice',
  (row_number() over (order by n.bid_ntce_date desc, n.bid_ntce_no) - 1)::int,
  '/notices/' || n.bid_ntce_no,
  n.updated_at
from (
  -- 같은 공고가 차수(bid_ntce_ord)별로 여러 행이라 공고번호당 최신 1행만.
  -- 사이트맵 공고 세그먼트는 PER_SEGMENT(10,000)개만 싣는다.
  -- 33만 행 전체를 정렬하지 않도록 bid_ntce_date 인덱스로 최신 15,000행만 뜬 뒤 중복 제거
  -- (중복률 약 12% → 10,000개는 남는다).
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

-- refresh ... concurrently 에 유니크 인덱스가 필요하고, 라우트 조회도 이 인덱스를 탄다.
create unique index if not exists sitemap_urls_kind_seq_idx on sitemap_urls (kind, seq);

grant select on sitemap_urls to service_role;

-- 최초 적재. Disk IO 소진 상태에선 DB 기본 statement_timeout(2분)을 넘기므로 세션에서 푼다.
set statement_timeout = 0;
refresh materialized view sitemap_urls;

-- 매일 08:00 KST (23:00 UTC) 갱신. daily-sync(20:00 UTC) 와 enrich-companies 가 끝난 뒤.
-- PostgREST RPC 는 statement_timeout 8초에 걸리므로 DB 안에서 pg_cron 으로 돌린다.
-- cron 세션에도 2분 기본값이 적용되므로 명령 안에서 먼저 푼다 (PG13+ 는 문장별 적용).
create extension if not exists pg_cron;
select cron.schedule(
  'refresh-sitemap-urls',
  '0 23 * * *',
  $$set statement_timeout = 0; refresh materialized view concurrently sitemap_urls$$
);
