-- 0053: 첨부 추출·요약 대상을 "경쟁입찰 + 추정가 1억 이상"으로 좁힌다 (2026-10-23).
--
-- 근거: 요약은 Haiku Message Batches 로 공고당 약 12원. 첨부 있는 공고 하루 1,230건(경쟁 645·수의 585)을
-- 전부 돌리면 월 44만 원, 경쟁만 23만 원. 1억 이상 경쟁은 하루 ~388건 → 월 14만 원(Anthropic 크레딧 $200 안).
-- 수의계약은 0029 에서 이미 제외. 추출(next_bid_notices_for_documents)도 같은 조건으로 — 문서 텍스트는
-- 요약 말고 쓰는 곳이 없어 추출만 해 두면 저장·시간 낭비. 추출 150건/회 × 하루 4~5회 = 600~750 ≥ 388 이라
-- documents-sync.yml 의 --limit 은 그대로.
-- 금액(presmpt_prce·asign_bdgt_amt 둘 다) 없는 공고(하루 ~40건)는 대상에서 빠진다.
-- 롤백: 0029(요약)·0021(추출) 의 함수 정의를 다시 실행.

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
     and coalesce(n.presmpt_prce, n.asign_bdgt_amt) >= 100000000
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
     and coalesce(n.presmpt_prce, n.asign_bdgt_amt) >= 100000000
     and not exists (
       select 1 from bid_notice_insights i
        where i.bid_ntce_no = n.bid_ntce_no and i.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;
