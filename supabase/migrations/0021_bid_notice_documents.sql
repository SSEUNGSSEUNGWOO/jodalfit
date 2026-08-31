-- 입찰공고 첨부파일 본문 텍스트 (제안요청서·공고문 등)
-- 파일 원본은 저장하지 않음 (나라장터 URL로 재다운로드 가능). 추출 텍스트만 보관.
-- 채우는 잡: jobs/extract_bid_documents.py (bid_notices.attachments 기준, 0020)

create table bid_notice_documents (
  bid_ntce_no   text not null,
  bid_ntce_ord  text not null,
  seq           int  not null,           -- attachments[].seq
  file_name     text,
  url           text not null,
  ext           text,                    -- hwp | hwpx | pdf | 기타
  status        text not null,           -- ok | skipped(미지원 확장자) | unsupported(배포용/암호 hwp) | empty | error
  error         text,
  text          text,
  char_count    int,
  fetched_at    timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord, seq),
  foreign key (bid_ntce_no, bid_ntce_ord) references bid_notices (bid_ntce_no, bid_ntce_ord) on delete cascade
);
create index bid_notice_documents_status_idx on bid_notice_documents (status);

-- 다른 테이블과 동일: service_role(백엔드)만 접근. anon 정책 없음.
alter table bid_notice_documents enable row level security;


-- 처리 대상 선정: 첨부 있고 아직 문서 row가 하나도 없는 진행 중 공고, 최신순.
-- (PostgREST로는 NOT EXISTS 표현이 안 돼 RPC로.)
create or replace function next_bid_notices_for_documents(p_limit int default 200)
returns table (bid_ntce_no text, bid_ntce_ord text, attachments jsonb)
language sql
stable
as $$
  select n.bid_ntce_no, n.bid_ntce_ord, n.attachments
    from bid_notices n
   where n.attachments is not null
     and n.bid_clse_date >= current_date
     and not exists (
       select 1 from bid_notice_documents d
        where d.bid_ntce_no = n.bid_ntce_no and d.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;
