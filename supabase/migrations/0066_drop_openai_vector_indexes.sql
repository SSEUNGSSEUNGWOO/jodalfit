-- supabase/migrations/0066_drop_openai_vector_indexes.sql
-- OpenAI 공간(`embedding`, 1536d)의 벡터 인덱스 3개를 지운다. 2026-11-05 psycopg 로 운영에 적용 완료(기록용).
--
-- 왜: 운영은 2026-10-15부터 kure(`embedding_k`)이고, OpenAI 3-small 은 10/15·11/05 채점표에서 KURE 보다 못해
-- 돌아갈 일이 없다. 이 인덱스를 읽는 건 `EMBED_SPACE=openai` 의 RPC(match_bid_notices 등 `_k` 없는 쪽)뿐인데
-- 운영·하네스(`--space` 기본값 = settings.embed_space) 모두 kure 라 아무도 안 읽었다. 디스크 2.5GB 즉시 반환(19GB → 17GB).
--
-- 응답 속도와는 무관하다 — 안 읽는 페이지는 캐시 자리를 차지하지 않는다. 디스크·백업 시간·정리 목적이다.
--
-- 열(`embedding`, `embedded_at`)과 `_k` 없는 RPC 4개는 남겨 둔다. 열을 지워도 공간은 테이블을 다시 써야(VACUUM FULL, 10GB 표 잠금)
-- 돌아오고, jobs/backfill_companies_basic·check_business_status·evaluate_recommendations·docs/recommender/scripts/export_embed_texts*
-- 가 `embedding is not null` 을 이름으로 읽는다. Gemini 768d 전환 때 KURE 열과 함께 한 번에 정리한다.
--
-- 되돌리기(필요할 리 없지만): 0032 의 ivfflat halfvec 패턴으로 재생성 — 416k 행이라 수십 분.

drop index concurrently if exists bid_notices_embedding_ivf_idx;   -- 2,452 MB
drop index concurrently if exists pre_specs_embedding_idx;         -- 20 MB
drop index concurrently if exists order_plans_embedding_idx;       -- 272 kB
