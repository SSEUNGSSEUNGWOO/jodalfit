-- 조건 검색 백엔드 — 키워드(제목·요약·키워드) + 발주기관 검색용 trgm 인덱스와 검색 RPC.
--
-- 입구 실사용 검색의 52% 가 키워드("감리", "태양광", "MIS")인데 /notices 조건 검색에는 키워드가 없었다.
-- 한국어 형태소 없이 tsvector 는 어절 단위라 "감리"가 "건설사업관리(감리)용역"에 안 걸린다 — companies 검색과
-- 같은 pg_trgm + ilike 로 간다. 제목이 1순위, 첨부 요약(bid_notice_insights.summary/keywords)은 보조:
-- 요약은 활성 공고의 60% 에만 있다(2026-10-16: 9,847 중 5,936).
--
-- 부분 인덱스 조건에 current_date 는 못 쓴다(IMMUTABLE 이어야 함). 고정 하한 ACTIVE_FLOOR = 2026-09-01 을 두고
-- RPC 도 같은 상수를 WHERE 에 넣어 planner 가 부분 인덱스를 고르게 한다. 하한은 활성 공고(마감 ≥ 오늘)를
-- 넉넉히 덮으면 되므로 몇 달에 한 번 날짜를 올려 재생성하면 된다(인덱스는 그 사이 조금씩 커질 뿐).
-- 2026-10-16: 마감 ≥ 2026-09-01 인 공고 55,124건, 그중 활성 9,847건.
--
-- 적용: psycopg 직결(0047~0049 와 같은 길). create index concurrently 는 트랜잭션 밖에서 — 아래 begin/commit 은
-- 함수 부분에만 걸려 있다.

-- 1) 제목
create index concurrently if not exists bid_notices_nm_trgm_active_idx
  on bid_notices using gin (bid_ntce_nm gin_trgm_ops)
  where bid_clse_date >= date '2026-09-01';

-- 2) 발주기관 — 수요기관·공고기관을 한 식으로. RPC 도 같은 식을 쓴다.
create index concurrently if not exists bid_notices_instt_trgm_active_idx
  on bid_notices using gin ((coalesce(dmnd_instt_nm, '') || ' ' || coalesce(ntce_instt_nm, '')) gin_trgm_ops)
  where bid_clse_date >= date '2026-09-01';

-- 3) 첨부 요약 + 키워드 — 공고 날짜가 없어 부분 인덱스 불가. 3.2만 행·45MB 라 전체 인덱스로.
-- array_to_string 은 STABLE 이라 인덱스 식에 바로 못 쓴다 — text[] 에 한해서는 결과가 바뀔 일이 없으니
-- IMMUTABLE 래퍼로 감싼다. RPC 도 같은 함수를 써야 인덱스를 탄다.
create or replace function insight_search_text(summary text, keywords text[])
returns text language sql immutable parallel safe as $$
  select coalesce(summary, '') || ' ' || coalesce(array_to_string(keywords, ' '), '')
$$;

create index concurrently if not exists bid_notice_insights_text_trgm_idx
  on bid_notice_insights using gin (insight_search_text(summary, keywords) gin_trgm_ops);

begin;

-- 2글자 검색("감리", "용역")은 trgm 이 트라이그램을 못 뽑아 GIN 이 인덱스 전체(5.5만)를 돌려주고 재검사에 530ms 가
-- 걸렸다(2026-10-16 실측, 요약 쪽은 3.2만 재검사에 1.3초). 그래서 3글자 미만이면 제목은 인덱스를 안 타는 strpos 로
-- 활성 공고(마감 ≥ 오늘, 약 1만 건)만 훑고, 요약·키워드는 아예 보지 않는다. ilike 특수문자(% _ \)는 이스케이프한다.
-- 응답 컬럼은 match_bid_notices(0049) 와 같고, similarity 대신 total_count(필터 전체 건수, 모든 행에 같은 값)와
-- title_hit(제목에 걸렸으면 true, 요약에만 걸렸으면 false) 를 붙였다.
-- 같은 공고번호의 여러 차수는 최신 차수 하나만 돌려준다(/notices 목록과 같은 규칙).
-- rgn 은 참가가능지역 문자열 부분 일치 — 기존 /notices 필터(applyFilters)와 같은 뜻. 지역 제한 없는 공고는 안 잡힌다.
-- sort: 'close'(마감 임박순, 기본) | 'price_desc'(추정가) | 'ntce_desc'(등록일). 키워드가 있으면 그 안에서 제목 적중이 먼저.
create or replace function search_bid_notices(
  q text default null,
  bsns_div text default null,
  rgn text default null,
  instt text default null,
  prc_min bigint default null,
  prc_max bigint default null,
  clse_from date default null,
  clse_to date default null,
  industry text default null,
  prdct_code text default null,
  lim int default 50,
  off int default 0,
  sort text default 'close'
)
returns table (
  bid_ntce_no text, bid_ntce_ord text, bid_ntce_nm text, bsns_div_nm text,
  bid_ntce_date date, bid_clse_date date, openg_date date, presmpt_prce bigint,
  ntce_instt_nm text, dmnd_instt_nm text, bidprc_psbl_indstryty_nm text,
  rgn_lmt_yn char(1), prtcpt_psbl_rgn_nm text, indstryty_lmt_yn char(1), bid_ntce_url text,
  title_hit boolean, total_count bigint
)
language sql stable as $$
  with kw as (
    select nullif(trim(q), '') as raw,
           '%' || replace(replace(replace(nullif(trim(q), ''), '', '\'), '%', '\%'), '_', '\_') || '%' as pat
  ),
  -- 키워드 적중: 제목(부분 인덱스, 활성 범위) ∪ 요약·키워드(insights 인덱스, 3글자 이상). 키워드가 없으면 비어 있다.
  hits as (
    select b.bid_ntce_no, b.bid_ntce_ord, true as title_hit
    from bid_notices b, kw
    where kw.raw is not null and length(kw.raw) >= 3
      and b.bid_clse_date >= date '2026-09-01'
      and b.bid_clse_date >= coalesce(clse_from, current_date)
      and b.bid_ntce_nm ilike kw.pat
    union all
    select b.bid_ntce_no, b.bid_ntce_ord, true
    from bid_notices b, kw
    where kw.raw is not null and length(kw.raw) < 3
      and b.bid_clse_date >= date '2026-09-01'
      and b.bid_clse_date >= coalesce(clse_from, current_date)
      and strpos(lower(b.bid_ntce_nm), lower(kw.raw)) > 0
    union all
    select i.bid_ntce_no, i.bid_ntce_ord, false
    from bid_notice_insights i, kw
    where kw.raw is not null and length(kw.raw) >= 3
      and insight_search_text(i.summary, i.keywords) ilike kw.pat
  ),
  best as (
    select bid_ntce_no, bid_ntce_ord, bool_or(title_hit) as title_hit
    from hits group by 1, 2
  ),
  filtered as (
    select distinct on (b.bid_ntce_no)
           b.bid_ntce_no, b.bid_ntce_ord, b.bid_ntce_nm, b.bsns_div_nm,
           b.bid_ntce_date, b.bid_clse_date, b.openg_date, b.presmpt_prce,
           b.ntce_instt_nm, b.dmnd_instt_nm, b.bidprc_psbl_indstryty_nm,
           b.rgn_lmt_yn, b.prtcpt_psbl_rgn_nm, b.indstryty_lmt_yn, b.bid_ntce_url,
           coalesce(h.title_hit, false) as title_hit
    from bid_notices b
    cross join kw
    left join best h on h.bid_ntce_no = b.bid_ntce_no and h.bid_ntce_ord = b.bid_ntce_ord
    where b.bid_clse_date >= date '2026-09-01'
      and b.bid_clse_date >= coalesce(clse_from, current_date)
      and (clse_to is null or b.bid_clse_date <= clse_to)
      and (kw.raw is null or h.bid_ntce_no is not null)
      and (bsns_div is null or b.bsns_div_nm = bsns_div)
      and (rgn is null or b.prtcpt_psbl_rgn_nm ilike '%' || rgn || '%')
      and (instt is null
           or (coalesce(b.dmnd_instt_nm, '') || ' ' || coalesce(b.ntce_instt_nm, '')) ilike '%' || instt || '%')
      and (prc_min is null or b.presmpt_prce >= prc_min)
      and (prc_max is null or b.presmpt_prce < prc_max)
      and (industry is null or position(industry in coalesce(b.bidprc_psbl_indstryty_nm, '')) > 0)
      and (prdct_code is null or b.prdct_clsfc_nos @> array[prdct_code])
    order by b.bid_ntce_no, b.bid_ntce_ord desc
  )
  select f.bid_ntce_no, f.bid_ntce_ord, f.bid_ntce_nm, f.bsns_div_nm,
         f.bid_ntce_date, f.bid_clse_date, f.openg_date, f.presmpt_prce,
         f.ntce_instt_nm, f.dmnd_instt_nm, f.bidprc_psbl_indstryty_nm,
         f.rgn_lmt_yn, f.prtcpt_psbl_rgn_nm, f.indstryty_lmt_yn, f.bid_ntce_url,
         f.title_hit, count(*) over () as total_count
  from filtered f
  order by f.title_hit desc,
           case when sort = 'price_desc' then f.presmpt_prce end desc nulls last,
           case when sort = 'ntce_desc' then f.bid_ntce_date end desc nulls last,
           f.bid_clse_date asc, f.bid_ntce_no
  limit greatest(lim, 0) offset greatest(off, 0);
$$;

notify pgrst, 'reload schema';

commit;
