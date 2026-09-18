-- 회사 페이지·추천 백엔드가 디스크 I/O에 묶여 느린 원인 두 곳 (2026-09-18 실측, explain analyze).
--
-- 1) institution_repeat_stats(협업 시그널, 추천마다 호출): (dmnd_instt_nm, cntrct_cncls_date) 인덱스는
--    타지만 count(distinct rprsnt_corp_bizrno_norm) 때문에 힙 4,476블록을 읽어 12.9초.
--    → rprsnt_corp_bizrno_norm 을 include 해 index-only scan. 실측 0.42초.
-- 2) 회사 페이지 fetchPeerRateByInstitution: bid_notices.dmnd_instt_nm 인덱스가 없어 4.2GB 풀스캔 5.8초.
--
-- 프로덕션에는 pg_cron 1회성 잡으로 `create index concurrently` 를 이미 적용했다 (MCP/Dashboard 세션은
-- 트랜잭션이라 concurrently 불가). 미적용 환경에서는 아래를 그대로 실행하면 된다.
--
-- 같은 날 발견: bid_notices_embedding_idx(HNSW) 가 indisvalid=false 로 남아 있었다 (과거 동시 빌드 실패 잔재,
-- idx_scan 0). 공고 벡터 검색(match_bid_notices, similar_notice_awardees)이 전부 브루트포스였던 원인.
-- `reindex index concurrently bid_notices_embedding_idx` 로 재생성 (역시 pg_cron 경유). 스키마 변경 아님.

create index if not exists contracts_instt_date_winner_idx
  on contracts (dmnd_instt_nm, cntrct_cncls_date) include (rprsnt_corp_bizrno_norm);

create index if not exists bid_notices_dmnd_instt_idx
  on bid_notices (dmnd_instt_nm);
