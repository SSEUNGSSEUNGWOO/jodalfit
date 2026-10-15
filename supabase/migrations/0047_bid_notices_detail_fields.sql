-- 상세 API(BidPublicInfoService)에만 오는 필드 4개를 bid_notices 에 싣는다.
--
-- 매시간 수집하는 표준 API(PubDataOpnStdService)는 53개 필드뿐이라 물품분류번호·사전규격 번호·
-- 참가자격 등록 마감·공동수급 방식이 없다(2026-10-15 실측: 활성 물품 공고 600건 중 상세 응답을 가진
-- 19건에만 존재). 채우는 쪽은 jobs/ingest_bid_notices_full.py 의 2차 패스(--fill).
--
-- prdct_clsfc_nos: 물품 통로용. 회사 쪽 company_supply_products.dtl_prdct_clsfc_no 와 같은 10자리 코드.
--   purchsObjPrdctList '[1^4227171301^이름],[1^...]' 에서 코드만 뽑아 배열로 — 한 공고에 여러 품목이 흔하다.
--   업종 통로(0044)와 같은 구조로 쓰려고 GIN.
-- bf_spec_rgst_no: 사전규격 등록번호. 지금은 공고번호로 추측해 잇고 있어 187건뿐 — 이걸로 직접 잇는다.
-- bid_qlfct_rgst_dt: 입찰참가자격 등록 마감. 입찰 마감보다 먼저 닫히는 진짜 데드라인.
-- cmmn_spldmd_methd_nm: 공동수급 방식(단독/공동 허용 여부).

begin;

alter table bid_notices
  add column if not exists prdct_clsfc_nos      text[],
  add column if not exists bf_spec_rgst_no      text,
  add column if not exists bid_qlfct_rgst_dt    timestamptz,
  add column if not exists cmmn_spldmd_methd_nm text;

create index if not exists bid_notices_prdct_clsfc_nos_gin
  on bid_notices using gin (prdct_clsfc_nos);

create index if not exists bid_notices_bf_spec_rgst_no_idx
  on bid_notices (bf_spec_rgst_no)
  where bf_spec_rgst_no is not null;

commit;
