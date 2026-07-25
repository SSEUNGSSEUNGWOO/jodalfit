-- ====================================================================
-- notice_events: 추천 노출/클릭 행동 로그 (recommender v2 A/B + 미래 learn-to-rank 대비)
--
-- search_logs(검색 단위)와 분리 — 이건 "공고 단위" 이벤트.
-- impression은 백엔드가 응답 시점에 batch 기록, click은 프론트 beacon.
-- ====================================================================

create table if not exists notice_events (
  id bigserial primary key,
  session_id text,
  target_bizrno text,        -- 조회 대상 회사 (키워드 모드면 null)
  event_type text not null,  -- 'impression' | 'click' | 'save' | 'dismiss' | 'subscribe'
  bid_ntce_no text not null,
  bid_ntce_ord text,
  rank_position int,         -- impression/click 시 몇 번째였는지
  algorithm_version text,    -- 'v1' | 'v2' 등 A/B 실험용
  score float,               -- 그 순간의 추천 score
  metadata jsonb,
  created_at timestamptz default now()
);

create index if not exists notice_events_target_idx
  on notice_events (target_bizrno, created_at desc);
create index if not exists notice_events_bid_idx
  on notice_events (bid_ntce_no, event_type);

-- 백엔드 service_role만 쓰기/읽기 (anon 차단)
alter table notice_events enable row level security;

comment on table notice_events is
  '추천 공고 노출/클릭 이벤트 로그. algorithm_version으로 v1/v2 A/B 비교, 장기적으로 learn-to-rank label 축적.';
