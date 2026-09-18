-- 실사용자가 검색했는데 companies 에 없던 사업자번호를 조달청(UsrInfoService02)에서 조회한 기록.
-- jobs/register_searched_companies 가 매시 쓴다. 조달업체로 등록되지 않은 번호(not_found)는
-- 7일 동안 다시 조회하지 않아 일일 API 한도(4,500)를 아낀다.
-- 2026-09-18 기준 "회사를 찾을 수 없음" 사업자번호 8개 중 5개가 조달청엔 등록돼 있었다(계약·참가 이력이 없어 수집 대상이 아니었음).

create table if not exists company_lookup_attempts (
  bizrno_norm  text primary key,
  result       text not null,          -- registered | not_found | error
  corp_nm      text,
  n_industries int,
  n_supplies   int,
  vector_built boolean,
  detail       text,
  checked_at   timestamptz not null default now()
);
