-- supabase/migrations/0070_match_pre_specs_doc_url.sql
-- match_pre_specs_g 반환에 규격서 첨부파일 URL(spec_doc_file_url_1) 을 더한다.
--
-- 결과 화면 "골든타임" 줄의 사전규격 행은 누를 데가 없었다 — 사이트에 사전규격 상세 페이지가 없고, 나라장터 사전규격 API 는
-- 공고와 달리 상세 페이지 URL 을 주지 않는다. 주는 건 규격서 파일 URL 네 칸뿐이고 DB 에는 있는데(ingest_pre_specs) RPC 가 안 돌려줘
-- 화면까지 못 왔다. 2026-11-09 실측: 의견 접수 중 1,798건 중 1,552건(86%)이 첫 번째 파일 URL 을 갖고 있다.
-- 행의 제목을 그 파일로 여는 링크로 바꾼다(frontend LeadsLine). 파일이 없는 행은 지금처럼 글줄.
--
-- gemini 공간(0067) 함수만 바꾼다 — kure 열은 11/06 전환 시점에 멈춰 있어 롤백해도 사전규격 추천은 그때 것이다.
-- 반환 컬럼이 늘어 replace 가 안 된다 — drop 후 create. 되돌리기 = 0067 의 match_pre_specs_g 절 재실행.
-- Dashboard SQL Editor 또는 psycopg 로 실행. 읽기 전용 함수라 운영에 바로 적용해도 무해.

drop function if exists match_pre_specs_g(vector, int, date);

create function match_pre_specs_g(
  query_embedding vector(768),
  match_count int default 50,
  min_opnin_clse_date date default null
)
returns table (
  bf_spec_rgst_no text, bid_ntce_no_list text, prdct_clsfc_no_nm text, bsns_div_nm text,
  sw_biz_obj_yn char(1), asign_bdgt_amt bigint, rgst_dt timestamptz, opnin_rgst_clse_dt timestamptz,
  order_instt_nm text, rl_dminstt_nm text, prdct_dtl_list text, ref_no text,
  spec_doc_file_url_1 text, similarity real
)
language sql
stable
as $$
  select s.bf_spec_rgst_no, s.bid_ntce_no_list, s.prdct_clsfc_no_nm, s.bsns_div_nm,
         s.sw_biz_obj_yn, s.asign_bdgt_amt, s.rgst_dt, s.opnin_rgst_clse_dt,
         s.order_instt_nm, s.rl_dminstt_nm, s.prdct_dtl_list, s.ref_no,
         s.spec_doc_file_url_1,
         (1 - (s.embedding_g <=> query_embedding))::real as similarity
  from pre_specs s
  where s.embedding_g is not null
    and (
      min_opnin_clse_date is null
      or s.opnin_rgst_clse_dt is null   -- 데이터 누락은 보수적으로 포함
      or s.opnin_rgst_clse_dt::date >= min_opnin_clse_date
    )
  order by s.embedding_g <=> query_embedding
  limit match_count;
$$;

-- 함수는 생성 시 PUBLIC 에 execute 가 붙는다 — 백엔드(service_role)만 남긴다(0057 과 같은 패턴).
grant execute on function match_pre_specs_g(vector, int, date) to service_role;
revoke execute on function match_pre_specs_g(vector, int, date) from public, anon, authenticated;
