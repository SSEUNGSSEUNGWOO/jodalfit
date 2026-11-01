-- 키워드 모드 좁히기(구분·마감) 사용 기록 — 2026-10-28 칩 배포 뒤 5일간 쓰였는지 잴 수 없었다(질의만 남았다).
-- 백엔드 log_search 가 키워드 모드에서 값이 있을 때만 채운다(회사 모드·칩 없음은 null).
-- 되돌리기: alter table search_logs drop column filter_div, drop column filter_due;
alter table search_logs
  add column if not exists filter_div text,     -- 물품 / 용역 / 공사
  add column if not exists filter_due int;      -- 마감까지 일수 상한(7 / 30)

comment on column search_logs.filter_div is '키워드 모드 좁히기 — 구분 칩(물품·용역·공사). 안 걸면 null';
comment on column search_logs.filter_due is '키워드 모드 좁히기 — 마감 칩(7·30일 이내). 안 걸면 null';
