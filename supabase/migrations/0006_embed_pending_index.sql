-- bid_notices 임베딩 대기 행 빠른 조회를 위한 partial index.
-- embed_bid_notices.py의 fetch_pending이 매일 cron마다 호출되는데
-- 218K 풀스캔 회피 목적. 임베딩 완료된 행은 인덱스에서 자동 제외.
create index if not exists bid_notices_embed_pending_idx
  on bid_notices (bid_ntce_no)
  where embedded_at is null;
