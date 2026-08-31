-- 첨부문서(제안요청서 등)에서 LLM으로 구조화한 공고 인사이트
-- 소스: bid_notice_documents(status='ok') → jobs/summarize_bid_documents.py (gpt-4o-mini, JSON schema)
-- 용도: 추천 설명 프롬프트(explain.py), 추천 응답 insight, 공고 상세 "문서 요약"
-- 주의: 공고 임베딩 텍스트에는 섞지 않음 (벡터 평균화로 짧은 질의 코사인 하락 실측)

create table bid_notice_insights (
  bid_ntce_no   text not null,
  bid_ntce_ord  text not null,
  summary       text,          -- 과업 요약 2~3문장
  scope         jsonb,         -- ["주요 과업 항목", ...]
  requirements  jsonb,         -- [{"kind":"license|certification|performance|region|company_size|other","text":"...","mandatory":true}]
  evaluation    jsonb,         -- {"method":"협상에 의한 계약","technical_pct":90,"price_pct":10,"presentation":true,"note":null}
  keywords      text[],        -- 기술·도메인 키워드
  source_seqs   int[],         -- 사용한 첨부 seq
  input_chars   int,
  model         text,
  created_at    timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord),
  foreign key (bid_ntce_no, bid_ntce_ord) references bid_notices (bid_ntce_no, bid_ntce_ord) on delete cascade
);
alter table bid_notice_insights enable row level security;


-- 처리 대상: 추출 성공 문서가 있고 아직 인사이트 없는 진행 중 공고, 최신순
create or replace function next_bid_notices_for_insights(p_limit int default 100)
returns table (bid_ntce_no text, bid_ntce_ord text)
language sql
stable
as $$
  select n.bid_ntce_no, n.bid_ntce_ord
    from bid_notices n
   where n.bid_clse_date >= current_date
     and exists (
       select 1 from bid_notice_documents d
        where d.bid_ntce_no = n.bid_ntce_no and d.bid_ntce_ord = n.bid_ntce_ord
          and d.status = 'ok'
     )
     and not exists (
       select 1 from bid_notice_insights i
        where i.bid_ntce_no = n.bid_ntce_no and i.bid_ntce_ord = n.bid_ntce_ord
     )
   order by n.bid_ntce_date desc nulls last, n.bid_ntce_no desc
   limit p_limit;
$$;
