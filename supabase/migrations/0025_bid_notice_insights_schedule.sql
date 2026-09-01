-- 인사이트에 일정 정보 추가 — 문서에 적힌 표현 그대로 (날짜 정규화 안 함).
-- {"start":"착수일","end":"2026. 12. 21.","duration":"착수일로부터 150일","delivery_deadline":null}
-- 기존 row는 null 유지 (앞으로 요약되는 공고부터 채움).

alter table bid_notice_insights add column if not exists schedule jsonb;
