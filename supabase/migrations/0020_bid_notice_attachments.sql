-- 입찰공고 첨부파일(제안요청서·공고서 등) 목록
-- 소스: BidPublicInfoService 응답의 ntceSpecDocUrl1~10 / ntceSpecFileNm1~10.
-- 형식: [{"seq":1,"name":"제안요청서.hwp","url":"https://www.g2b.go.kr/..."}]
-- 갱신은 jobs/ingest_bid_attachments.py → update_bid_notice_attachments RPC.

alter table bid_notices add column if not exists attachments jsonb;


-- UPDATE 전용 batch RPC (0004 임베딩 RPC와 같은 패턴 — upsert는 NOT NULL 컬럼 충돌)
create or replace function update_bid_notice_attachments(updates jsonb)
returns int
language plpgsql
as $$
declare
  rec record;
  cnt int := 0;
begin
  for rec in
    select * from jsonb_to_recordset(updates)
      as x(bid_ntce_no text, bid_ntce_ord text, attachments jsonb)
  loop
    update bid_notices
       set attachments = rec.attachments
     where bid_ntce_no = rec.bid_ntce_no
       and bid_ntce_ord = rec.bid_ntce_ord;
    if found then cnt := cnt + 1; end if;
  end loop;
  return cnt;
end;
$$;


-- 백필: ingest_bid_notices_full로 들어온 row는 raw에 첨부 필드가 이미 있음 → 그대로 변환.
-- 대량(수십만 건)이면 statement timeout 나므로 bid_ntce_date 월 단위로 나눠 실행.
update bid_notices b
   set attachments = a.att
  from (
    select n.bid_ntce_no, n.bid_ntce_ord,
           jsonb_agg(
             jsonb_build_object(
               'seq',  i,
               'name', n.raw->>('ntceSpecFileNm' || i),
               'url',  n.raw->>('ntceSpecDocUrl' || i)
             ) order by i
           ) as att
      from bid_notices n, generate_series(1, 10) i
     where coalesce(n.raw->>('ntceSpecDocUrl' || i), '') <> ''
       -- and n.bid_ntce_date >= '2026-01-01' and n.bid_ntce_date < '2026-02-01'
     group by n.bid_ntce_no, n.bid_ntce_ord
  ) a
 where b.bid_ntce_no = a.bid_ntce_no
   and b.bid_ntce_ord = a.bid_ntce_ord
   and b.attachments is null;
