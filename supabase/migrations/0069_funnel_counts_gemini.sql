-- supabase/migrations/0069_funnel_counts_gemini.sql
-- funnel_counts 의 "벡터 있음" 조건을 운영 임베딩 공간(gemini, `embedding_g`) 으로 옮긴다.
--
-- 0057 은 embedding_k(KURE) 를 봤다. 2026-11-06 운영을 gemini 로 전환한 뒤 새 공고는 embedding_g 만 채워지므로
-- 그대로 두면 "지금 입찰 가능한 공고" 가 날마다 줄어든다(2026-11-09: 최근 3일 열린 공고 1,733건 중 _k 532 / _g 1,594).
-- 같은 날 프런트 lib/entry.ts·companies/suggest·saved/companies 의 embedding_k 고정도 EMB_COL 로 바꿨다.
-- SQL 함수는 EMBED_SPACE 를 못 읽으므로 공간을 바꾸면 이 함수도 같이 바꾼다(롤백 = 0057 재실행).
--
-- 반환 컬럼·시그니처 그대로라 create or replace 로 충분하다. 읽기 전용 함수 — 운영에 바로 적용해도 무해.

create or replace function public.funnel_counts(p_names text[], p_days int default 90)
returns table (total bigint)
language sql
stable
as $$
  select count(*) as total
    from public.bid_notices n
   where n.bid_clse_date between current_date and current_date + p_days
     and n.embedding_g is not null
     and (n.bid_qlfct_rgst_dt is null or n.bid_qlfct_rgst_dt > now());
$$;

comment on function public.funnel_counts(text[], int) is
  'p_names 는 미사용 — 0057 에서 업종 칸을 지웠다. 벡터 열은 운영 임베딩 공간(0069: embedding_g) 을 따른다.';
