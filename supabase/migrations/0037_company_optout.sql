-- ====================================================================
-- 회사 정보 비공개 요청 (opt-out)
--
-- 나라장터 원본 계약정보는 공공데이터지만, 그것을 회사별로 취합·분석해 검색엔진에
-- 색인시키는 것은 별개 문제다. 정보주체(회사 대표)가 비공개를 요청하면 이 플래그를
-- 세우고, 그 회사는 사이트 어디에도 노출되지 않는다.
--
-- 행을 지우지 않고 플래그로 남기는 이유: jobs/register_searched_companies.py 가
-- "회사를 찾을 수 없음" 검색 로그를 보고 조달청 API로 회사를 자동 재생성한다.
-- 행을 삭제하면 누군가 그 사업자번호를 한 번 검색하는 것만으로 되살아난다.
-- (같은 잡이 companies 에 이미 있는 bizrno_norm 은 후보에서 빼므로, 행이 남아
--  있는 한 재등록되지 않는다.)
--
-- 매일 돌아가는 ingest/embed 잡의 upsert 는 명시한 컬럼만 쓰므로 이 플래그를
-- 덮어쓰지 않는다.
--
-- ── MV 를 건드리지 않는 이유 (중요) ──────────────────────────────────
-- sitemap_urls / industry_companies MV 정의에도 `optout_at is null` 을 넣으려
-- 했으나, MV 는 정의 변경이 안 돼 drop→create→refresh 가 필요하고 회사 6만 행
-- 기준 10분이 지나도 안 끝났다. 그동안 ACCESS EXCLUSIVE 락 때문에 사이트맵
-- 라우트가 500 을 냈다 (2026-09-21 실측 후 롤백).
-- 대신 MV 를 읽는 쪽(frontend/src/lib/optout.ts)에서 거른다. 비공개 요청은
-- 건수가 매우 적어 이 방식이 충분하고, 프로덕션 영향이 없다.
-- ====================================================================

alter table companies
  add column if not exists optout_at timestamptz,
  add column if not exists optout_note text;

comment on column companies.optout_at is
  '정보주체 비공개 요청 시각. null 이 아니면 사이트·사이트맵·검색·추천 전부에서 제외한다.';

-- ── 상호 검색 (pg_trgm) 에서 제외 ────────────────────────────────────
-- 0015 정의 + optout 제외. 검색으로도 잡히면 안 된다.
create or replace function public.find_companies(query_name text, max_count integer default 5)
returns table(bizrno text, corp_nm text, english_nm text, ceo_nm text, similarity real)
language sql
stable
as $function$
  select c.bizrno, c.corp_nm, c.english_nm, c.ceo_nm,
         greatest(
           similarity(c.corp_nm, query_name),
           coalesce(similarity(c.english_nm, query_name), 0)
         )::real as similarity
  from companies c
  where (c.corp_nm % query_name or c.english_nm % query_name)
    and not c.is_restricted
    and c.optout_at is null
  order by similarity desc
  limit max_count;
$function$;

-- ── 타사 페이지의 "유사 시장 상시 낙찰자" 에서 제외 ──────────────────
-- 0031 정의 + optout 제외. 이게 없으면 A사를 숨겨도 경쟁사 B·C 페이지에
-- A사 상호·사업자번호·낙찰 공고명이 계속 뜬다 (award_results 는 companies 와
-- 조인하지 않으므로 여기서 명시적으로 걸러야 한다).
create or replace function public.similar_notice_awardees(
  p_bizrno_norm text,
  p_similar_pool integer default 60,
  p_top_n integer default 10,
  p_history_limit integer default 30
)
returns table(bizrno text, corp_nm text, encounter_count integer, sample_notice_names text[])
language plpgsql
stable
as $function$
declare
  v_avg halfvec(1536);
begin
  select avg(bn.embedding)::halfvec(1536)
    into v_avg
    from (
      select ar.bid_ntce_no, ar.bid_ntce_ord
      from award_results ar
      where ar.bizrno_norm = p_bizrno_norm
        and ar.is_winner
      order by ar.bid_ntce_no desc
      limit p_history_limit
    ) cn
    join bid_notices bn
      on bn.bid_ntce_no = cn.bid_ntce_no
     and bn.bid_ntce_ord = cn.bid_ntce_ord
    where bn.embedding is not null;

  if v_avg is null then
    return;
  end if;

  perform set_config('ivfflat.probes', '10', true);

  return query
  with similar_notices as (
    select bn2.bid_ntce_no, bn2.bid_ntce_ord, bn2.bid_ntce_nm
    from bid_notices bn2
    order by bn2.embedding::halfvec(1536) <=> v_avg
    limit p_similar_pool
  ),
  competitor_awards as (
    select ar.bizrno_norm, ar.corp_nm, sn.bid_ntce_nm
    from similar_notices sn
    join award_results ar
      on ar.bid_ntce_no = sn.bid_ntce_no
     and ar.bid_ntce_ord = sn.bid_ntce_ord
    where ar.is_winner
      and ar.bizrno_norm is not null
      and ar.bizrno_norm <> ''
      and ar.bizrno_norm <> p_bizrno_norm
      and not exists (
        select 1 from companies c
        where c.bizrno_norm = ar.bizrno_norm
          and c.optout_at is not null
      )
  )
  select
    ca.bizrno_norm as bizrno,
    (array_agg(ca.corp_nm order by length(ca.corp_nm) desc))[1] as corp_nm,
    count(*)::int as encounter_count,
    (array_agg(distinct ca.bid_ntce_nm))[1:3] as sample_notice_names
  from competitor_awards ca
  group by ca.bizrno_norm
  order by encounter_count desc
  limit p_top_n;
end;
$function$;

-- ── 접수된 비공개 요청 ───────────────────────────────────────────────
-- 2026-09-18 수건설안전지도사사무소(462-63-00687) 대표 이메일 요청.
update companies
   set optout_at = coalesce(optout_at, now()),
       optout_note = '2026-09-18 대표자 이메일 비공개 요청'
 where bizrno_norm = '4626300687';
