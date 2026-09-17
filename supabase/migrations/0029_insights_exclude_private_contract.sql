-- 요약(bid_notice_insights) 대상에서 수의계약 공고 제외.
-- 2026-09 실측: 수의계약이 요약 모집단의 43%인데 추천 TOP 5 노출은 4%. 제외해도 노출 공고의 93%는 유지.
-- 0023 본문에 cntrct_cncls_mthd_nm 조건 한 줄 추가. Dashboard SQL Editor에서 실행.
--
-- 참고: summarize 잡이 OpenAI Batch 제출 중인 공고는 summary null·model='batch:<id>'인 placeholder 행으로
-- 남아 있어 아래 not exists에 자연히 걸린다 (중복 제출 방지). 스키마 변경 없음.

create or replace function next_bid_notices_for_insights(p_limit int default 100)
returns table (bid_ntce_no text, bid_ntce_ord text)
language sql
stable
as $$
  with docs as (
    select distinct d.bid_ntce_no, d.bid_ntce_ord
      from bid_notice_documents d
     where d.status = 'ok'
  )
  select n.bid_ntce_no, n.bid_ntce_ord
    from docs
    join bid_notices n
      on n.bid_ntce_no = docs.bid_ntce_no and n.bid_ntce_ord = docs.bid_ntce_ord
   where n.bid_clse_date >= current_date
     and n.cntrct_cncls_mthd_nm is distinct from '수의계약'
     and not exists (
       select 1 from bid_notice_insights i
        where i.bid_ntce_no = n.bid_ntce_no and i.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;
