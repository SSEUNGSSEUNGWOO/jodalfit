-- supabase/migrations/0056_funnel_counts.sql
-- 결과 페이지 "걸러낸 경로" 앞 두 칸 — 지금 입찰 가능한 공고 수(마감 p_days 일 이내)와 그중 회사 등록업종을 허용하는 공고 수.
-- 시안(gen_data.py::funnel)은 파이썬에서 전수를 돌렸다. 운영은 한 번의 집계로 — 두 수 모두 같은 범위(bid_clse_date 오늘~오늘+p_days).
-- 업종 허용 판정은 0044 의 업종 채널과 같은 기준(bidprc_psbl_indstryty_nm 에 등록업종 이름 포함). p_names 가 비면 industry = 0.
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 운영에 먼저 적용해도 무해(읽기 전용 함수).
create or replace function public.funnel_counts(p_names text[], p_days int default 90)
returns table (total bigint, industry bigint)
language sql
stable
as $$
  select count(*) as total,
         count(*) filter (
           where coalesce(array_length(p_names, 1), 0) > 0
             and exists (select 1 from unnest(p_names) nm where n.bidprc_psbl_indstryty_nm like '%' || nm || '%')
         ) as industry
    from public.bid_notices n
   where n.bid_clse_date between current_date and current_date + p_days;
$$;

grant execute on function public.funnel_counts(text[], int) to service_role;
revoke execute on function public.funnel_counts(text[], int) from anon, authenticated;
