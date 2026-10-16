-- 발주계획 ↔ 공고 직접 연결 컬럼.
--
-- 상세 API(BidPublicInfoService) 응답의 orderPlanUntyNo 가 그것이다 — 표준 API 에는 없어 raw 에만 있었고,
-- 공고 페이지는 order_plans.bid_ntce_no_list 에 공고번호가 들어 있는지(ilike)로 추측해 이었다(2026-10-16 기준 4건).
-- 사전규격(0047 bf_spec_rgst_no)과 같은 구조: 채우는 쪽은 jobs/ingest_bid_notices_full.py 의 2차 패스(--fill),
-- 읽는 쪽은 frontend/src/lib/notice.ts fetchLifecycle.
-- 값 형식은 두 가지가 섞여 있다: 나라장터 번호 'R26DD2xxxxxxx'(order_plans.order_plan_unty_no 와 같은 형식)와
-- 기관 자체 번호 '303100-2026-P-00100'. 후자는 order_plans 에 없어 이어지지 않는다.

begin;

alter table bid_notices
  add column if not exists order_plan_unty_no text;

create index if not exists bid_notices_order_plan_unty_no_idx
  on bid_notices (order_plan_unty_no)
  where order_plan_unty_no is not null;

-- 상세 API 로 이미 들어온 행은 raw 에 값이 있다 — API 를 다시 부르지 않고 그대로 옮긴다.
update bid_notices
   set order_plan_unty_no = nullif(raw->>'orderPlanUntyNo', '')
 where raw ? 'orderPlanUntyNo'
   and nullif(raw->>'orderPlanUntyNo', '') is not null
   and order_plan_unty_no is null;

commit;
