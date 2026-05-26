-- 사용자 검색 로그 — 어떤 회사명/키워드로 추천을 돌렸는지 본인용 분석 데이터.
-- 추천 응답 흐름과 분리(fire-and-forget)되어야 하므로 인덱스/제약은 최소.

create table if not exists search_logs (
  id                 bigserial primary key,
  query              text not null,
  mode               text not null,              -- company / keywords / auto
  matched_bizrno     text,
  matched_corp_nm    text,
  result_count       int default 0,
  kw_result_count    int default 0,
  has_error          boolean default false,
  error_msg          text,
  with_explanation   boolean default false,
  ip_hash            text,                       -- sha256(ip + salt) 앞 16자
  user_agent         text,
  referer            text,
  latency_ms         int,
  created_at         timestamptz not null default now()
);

create index if not exists search_logs_created_idx on search_logs (created_at desc);
create index if not exists search_logs_mode_idx on search_logs (mode, created_at desc);
