-- ====================================================================
-- jobs.ingest_bid_participants 의 큐 조회가 타임아웃 나던 것을 푼다
--
-- 큐 쿼리는 "최근 N일 낙찰 공고"(is_winner=true + bsns_div_nm + created_at >= since)다.
-- created_at 인덱스가 없어서 award_results_winner_idx(is_winner 부분 인덱스)만 타고
-- 낙찰 행 23.6만 건을 전부 긁은 뒤 Filter 로 11.5만 건을 버렸다.
-- 2026-09-28 실측: limit 1000 에 8.0초 (Buffers read=26,707) → statement timeout.
-- 그 결과 2026-09-20 부터 9일 연속 이 잡이 죽어 참가업체(경쟁사 투찰) 수집이 멈췄다.
--
-- 범위 조건이 걸리는 created_at 을 선두 키로 두고, 낙찰 행만 담는 부분 인덱스로
-- 최근 며칠 구간만 읽게 한다. bsns_div_nm 은 그 뒤 소수 행에만 걸리는 필터라 뺀다.
-- ====================================================================

create index if not exists award_results_winner_created_idx
  on award_results (created_at desc)
  where is_winner = true;
