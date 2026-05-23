-- 사업자번호 정규화
-- API 응답은 10자리 dashes 없는 형식, contracts는 dashes 섞임
-- generated column으로 자동 동기화. join은 _norm 컬럼 사용.

alter table companies
  add column bizrno_norm text
  generated always as (regexp_replace(coalesce(bizrno, ''), '\D', '', 'g')) stored;
create index companies_bizrno_norm_idx on companies (bizrno_norm);

alter table contracts
  add column rprsnt_corp_bizrno_norm text
  generated always as (regexp_replace(coalesce(rprsnt_corp_bizrno, ''), '\D', '', 'g')) stored;
create index contracts_corp_bizrno_norm_idx on contracts (rprsnt_corp_bizrno_norm);

alter table award_results
  add column bizrno_norm text
  generated always as (regexp_replace(coalesce(bizrno, ''), '\D', '', 'g')) stored;
create index award_results_bizrno_norm_idx on award_results (bizrno_norm);

alter table subscribers
  add column bizrno_norm text
  generated always as (regexp_replace(coalesce(bizrno, ''), '\D', '', 'g')) stored;
