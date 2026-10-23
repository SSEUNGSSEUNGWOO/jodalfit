-- supabase/migrations/0059_match_order_plans_not_noticed.sql
-- 발주계획 매칭에서 **이미 공고로 전환된 계획을 뺀다**. 반환에 bid_ntce_no_list 를 추가한다.
--
-- 왜: 발주계획은 "앞으로 나올 공고"라는 선행지표다. 이미 공고가 뜬 계획은 선행지표가 아니고,
-- 그 공고 자체가 메인 추천에 이미 들어 있다 — 같은 사업을 두 번 세게 된다.
-- 2026-10-23 확인: 한종산업개발의 발주계획 추천 20건과 사전규격 추천 4건에 같은 사업이 겹쳤다
-- ("거창군 공공하수도 관리대행 용역" 등).
--
-- 모수: 벡터 있는 발주계획 6,132건 중 공고 미전환 3,561건(58%). 연·월 조건은 걸지 않는다 —
-- 미전환분의 3,543건이 2026-10 한 달에 몰려 있어 거르는 의미가 없다(발주계획은 갱신 재공개된다).
--
-- 유사도 문턱은 여기 두지 않는다. 회사마다 유사도 척도가 달라(상위 20위 유사도가 0.540~0.755)
-- 고정값을 쓸 수 없다 — recommend.py 가 '그 회사에게 보여준 공고 중 가장 낮은 유사도'를 바닥으로 쓴다.
--
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 반환 컬럼이 늘어 drop 후 create.

begin;

drop function if exists match_order_plans_k(vector, int);

create function match_order_plans_k(
  query_embedding vector(1024),
  match_count int default 50
)
returns table (
  order_plan_unty_no text,
  biz_nm             text,
  bsns_div_nm        text,
  bsns_ty_nm         text,
  order_year         text,
  order_mnth         text,
  cntrct_mthd_nm     text,
  order_instt_nm     text,
  totlmng_instt_nm   text,
  sum_order_amt      bigint,
  prdct_clsfc_no_nm  text,
  usg_cntnts         text,
  spec_cntnts        text,
  ntice_dt           timestamptz,
  bid_ntce_no_list   text,
  similarity         real
)
language sql
stable
as $$
  select o.order_plan_unty_no, o.biz_nm, o.bsns_div_nm, o.bsns_ty_nm,
         o.order_year, o.order_mnth, o.cntrct_mthd_nm,
         o.order_instt_nm, o.totlmng_instt_nm, o.sum_order_amt,
         o.prdct_clsfc_no_nm, o.usg_cntnts, o.spec_cntnts, o.ntice_dt,
         o.bid_ntce_no_list,
         (1 - (o.embedding_k <=> query_embedding))::real as similarity
    from order_plans o
   where o.embedding_k is not null
     and coalesce(o.bid_ntce_no_list, '') = ''   -- 이미 공고가 뜬 계획은 선행지표가 아니다
   order by o.embedding_k <=> query_embedding
   limit match_count;
$$;

commit;
