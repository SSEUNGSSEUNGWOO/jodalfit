-- 0022의 next_bid_notices_for_insights가 statement timeout(57014).
-- bid_notices(3.9GB)를 바깥에 두고 EXISTS를 걸면 플래너가 seq scan을 타서 8초 초과.
-- 작은 쪽(bid_notice_documents, status='ok')에서 출발해 PK로 조인하도록 재작성.

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
     and not exists (
       select 1 from bid_notice_insights i
        where i.bid_ntce_no = n.bid_ntce_no and i.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;
