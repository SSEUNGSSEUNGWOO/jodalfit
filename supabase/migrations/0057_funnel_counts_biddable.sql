-- supabase/migrations/0057_funnel_counts_biddable.sql
-- 결과 페이지 "걸러낸 경로" 첫 칸을 파이프라인이 실제로 볼 수 있는 공고 수로 바꾼다.
--
-- 0056 의 total 은 bid_clse_date 만 봤다. 그래서 두 가지가 섞여 있었다:
--   1) 입찰참가자격 등록 마감이 이미 지난 공고 — 지금 등록하려는 업체는 낼 수 없다.
--      0049 가 후보 검색에서 빼고 있는데 깔때기에는 세고 있었다. 2026-10-23 기준 1,675건.
--      실측으로도 빼는 게 맞다: 과거 낙찰 공고 중 그 시점에 자격등록이 이미 마감이던 것이
--      8/1 은 4,101건 중 52건(1.3%), 9/1 은 2,062건 중 2건(0.1%).
--   2) 벡터가 없는 공고 — 유사도 검색 대상이 아니다. (2026-10-23 현재 0건이지만 조건은 맞춘다)
-- 합치면 9,900 → 8,225. "지금 입찰 가능한 공고"라고 적어놓고 못 내는 걸 세면 안 된다.
--
-- industry(등록업종 허용 공고 수)는 **지운다**. 깔때기의 한 칸이 아니었다 —
-- 후보 풀은 이 집합에서 꺼내는 게 아니라 전체 공고에서 유사도 순으로 뽑는다.
-- 2026-10-23 확인(한종산업개발, 최종 20건): 등록업종 허용 9건 / 업종 제한 없음 3건 /
-- 업종 불일치 8건. 40%가 이 집합 밖이라 "845 안에서 200을 꺼냈다"는 그림은 거짓이다.
-- 머리 장면은 8,225 → 후보 → 자격 통과 → 추천 네 칸으로 간다(전부 앞 칸의 부분집합).
--
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 운영에 먼저 적용해도 무해(읽기 전용 함수).

-- 시그니처가 (text[], int) 그대로지만 반환 컬럼이 줄어 replace 가 안 된다 — drop 후 create.
drop function if exists public.funnel_counts(text[], int);

create function public.funnel_counts(p_names text[], p_days int default 90)
returns table (total bigint)
language sql
stable
as $$
  select count(*) as total
    from public.bid_notices n
   where n.bid_clse_date between current_date and current_date + p_days
     and n.embedding_k is not null
     and (n.bid_qlfct_rgst_dt is null or n.bid_qlfct_rgst_dt > now());
$$;

-- p_names 는 쓰지 않지만 호출부 호환을 위해 남긴다(인자를 빼면 배포 순서에 따라 깨진다).
comment on function public.funnel_counts(text[], int) is
  'p_names 는 미사용 — 0057 에서 업종 칸을 지웠다. 다음 정리 때 인자도 뺀다.';

grant execute on function public.funnel_counts(text[], int) to service_role;
-- 함수는 생성 시 PUBLIC 에 execute 가 붙는다 — service_role 만 남긴다.
revoke execute on function public.funnel_counts(text[], int) from public, anon, authenticated;
