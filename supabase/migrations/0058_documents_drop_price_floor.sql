-- supabase/migrations/0058_documents_drop_price_floor.sql
-- 첨부 추출·요약 대상에서 **추정가 1억 하한을 뺀다**. 경쟁입찰 조건은 유지.
--
-- 0053 이 하한을 넣은 근거가 틀린 비용 추정이었다. "월 44만 원 → 14만 원"이라고 했는데
-- 2026-10-23 실측(bid_notice_insights.input_chars, 최근 30일 12,750건)으로 다시 내니:
--   건당 입력 5,106 토큰(실측) · 출력 700 토큰(가정) · claude-haiku-4-5 · Batch 50%
--   → 건당 약 5.9원
--   1억 이상만:      월 9,300건  → 약 5.5만 원
--   금액 기준 없음:  월 16,483건 → 약 9.8만 원
-- 차이가 월 4만 원이다. 10배 과대 추정으로 작은 공고를 통째로 버리고 있었다.
--
-- 금액 하한은 제품 관점에서도 거꾸로였다. 1천만~5천만 구간이 월 2,971건인데 중소 SI 가
-- 실제로 노리는 규모다. 1억 넘는다고 아무도 안 볼 공고를 읽고, 노리는 공고는 안 읽고 있었다.
--
-- 수의계약 제외는 남긴다 — 경쟁입찰이 아니면 과업 내용을 읽어도 낼 수가 없다.
-- 남는 비용 걱정은 금액이 아니라 처리량으로 막는다(documents-sync 가 2시간마다 150/100 건).
--
-- Dashboard SQL Editor 에서 실행 (CLI 아님). 읽기 전용 함수라 운영에 먼저 적용해도 무해.

create or replace function next_bid_notices_for_documents(p_limit int default 200)
returns table (bid_ntce_no text, bid_ntce_ord text, attachments jsonb)
language sql
stable
as $$
  select n.bid_ntce_no, n.bid_ntce_ord, n.attachments
    from bid_notices n
   where n.attachments is not null
     and n.bid_clse_date >= current_date
     and n.cntrct_cncls_mthd_nm is distinct from '수의계약'
     and not exists (
       select 1 from bid_notice_documents d
        where d.bid_ntce_no = n.bid_ntce_no and d.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;

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
