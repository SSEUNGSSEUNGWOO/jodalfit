-- 회사 페이지 SSR 추천 결과 캐시 (read-through).
--
-- /companies/[bizrno]는 렌더마다 POST /recommendations를 부르고, 그 한 번이
-- Supabase 왕복 12회+와 LLM 총평 1회를 쓴다. 실측 p50 26초.
--
-- 측정 근거 (2026-07-03 ~ 08-28, SSR 요청 19,788건):
--   고유 회사 6,543개 / 재방문 13,245건 = 66.9%  ← 캐시 히트율 상한
--   최다 방문 회사는 55일간 526회.
-- 짧은 창(14시간)만 보면 재방문이 없어 보이지만 크롤러는 주 단위로 재방문한다.
--
-- payload는 recommend() 응답을 그대로 담는다. 참조만 저장하고 읽을 때 조인하는
-- 방식이 용량은 작지만, 사전규격 섹션이 저장된 전체 목록을 골든타임 기준으로
-- 재정렬해 상위를 고르는 등 표시 로직이 원본 목록에 의존해서 그대로 두는 편이 안전하다.
-- 회사당 약 45KB. 현재 실수요 6,543개 기준 ~290MB.
-- 커버리지가 크게 늘면 results의 score_breakdown/qualification(회사 페이지 미사용)을
-- 떼는 것이 첫 번째 절감 레버다.
--
-- 무효화는 시간이 아니라 내용 기준이다. 0018로 마감 지평선이 D+90으로 잘려서
-- 저장된 공고는 90일 안에 전부 마감된다. 읽을 때 마감 지난 건을 걷어내고,
-- 남은 게 임계값 미만이면 재계산한다.

create table if not exists company_recommendations (
  bizrno_norm text primary key,
  algorithm   text not null,
  result_limit int not null,
  payload     jsonb not null,
  computed_at timestamptz not null default now()
);

create index if not exists company_recommendations_computed_at_idx
  on company_recommendations (computed_at);
