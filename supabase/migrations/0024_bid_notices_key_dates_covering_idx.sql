-- next_bid_notices_for_insights(0023)가 documents → bid_notices PK 조회를 1,400회 하면서
-- 힙 페이지를 랜덤 읽기 → Disk IO 예산 소진 상태에서 8초 초과(57014).
-- 날짜 컬럼을 include한 커버링 인덱스로 index-only scan 유도 (힙 접근 제거).

create index if not exists bid_notices_key_dates_idx
  on bid_notices (bid_ntce_no, bid_ntce_ord)
  include (bid_clse_date, bid_ntce_date);
