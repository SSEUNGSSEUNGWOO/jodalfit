-- supabase/migrations/0060_pre_specs_pending_embed_idx.sql
-- embed_pre_specs 의 대상 조회(embedding_k is null order by opnin_rgst_clse_dt desc nulls last limit N)용 부분 인덱스.
-- 2026-10-23 백필(54,943건)에서 처리량이 분당 3,600 → 200 건으로 떨어졌다. GPU 는 놀았고 병목은 이 조회 —
-- 이미 임베딩된 최근 행을 매 배치마다 훑고 지나가야 남은 null 행에 닿는다. 부분 인덱스면 null 행만 마감 순으로 바로 읽는다.
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 6만 행이라 수 초, 운영에 먼저 적용해도 무해.
create index if not exists pre_specs_pending_embed_k_idx
  on public.pre_specs (opnin_rgst_clse_dt desc nulls last)
  where embedding_k is null;
