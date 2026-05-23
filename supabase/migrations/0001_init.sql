-- jodalfit 초기 스키마
-- 데이터 라이프사이클: 발주계획 → 사전규격(+의견) → 입찰공고 → 낙찰/개찰 → 계약
-- 회사 시그널 3종: 수주(계약) + 관심(사전규격 의견) + 참여(개찰결과)

create extension if not exists vector;
create extension if not exists pg_trgm;

create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at := now();
  return new;
end;
$$ language plpgsql;


-- ====================================================================
-- 1. bid_notices : 입찰공고 (추천 대상)
-- 소스: PubDataOpnStdService/getDataSetOpnStdBidPblancInfo
-- ====================================================================
create table bid_notices (
  bid_ntce_no              text not null,
  bid_ntce_ord             text not null default '000',
  bid_ntce_nm              text not null,
  bsns_div_nm              text,
  bid_ntce_date            date,
  bid_clse_date            date,
  openg_date               date,
  presmpt_prce             bigint,
  asign_bdgt_amt           bigint,
  ntce_instt_cd            text,
  ntce_instt_nm            text,
  dmnd_instt_cd            text,
  dmnd_instt_nm            text,
  bidprc_psbl_indstryty_nm text,
  bidwinr_dcsn_mthd_nm     text,
  cntrct_cncls_mthd_nm     text,
  bid_ntce_url             text,
  rgn_lmt_yn               char(1),
  prtcpt_psbl_rgn_nm       text,
  indstryty_lmt_yn         char(1),
  elctrn_bid_yn            char(1),
  intrntnl_bid_yn          char(1),
  data_bss_date            date,
  raw                      jsonb not null,
  embedding                vector(1536),
  embedded_at              timestamptz,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord)
);
create index bid_notices_bsns_div_idx     on bid_notices (bsns_div_nm);
create index bid_notices_ntce_date_idx    on bid_notices (bid_ntce_date desc);
create index bid_notices_clse_date_idx    on bid_notices (bid_clse_date);
create index bid_notices_embedding_idx    on bid_notices using hnsw (embedding vector_cosine_ops);
create trigger trg_bid_notices_updated
  before update on bid_notices for each row execute function set_updated_at();


-- ====================================================================
-- 2. contracts : 계약 (회사 수주 시그널 ⭐)
-- 소스: PubDataOpnStdService/getDataSetOpnStdCntrctInfo
-- ====================================================================
create table contracts (
  cntrct_no              text not null,
  cntrct_ord             text not null default '01',
  unty_cntrct_no         text,
  bid_ntce_no            text,
  bid_ntce_ord           text,
  cntrct_nm              text,
  bsns_div_nm            text,
  cntrct_cncls_mthd_nm   text,
  cntrct_cncls_date      date,
  cntrct_amt             bigint,
  ttal_cntrct_amt        bigint,
  rsrvtn_prce            bigint,
  rprsnt_corp_bizrno     text,
  rprsnt_corp_nm         text,
  rprsnt_corp_ceo_nm     text,
  cntrct_instt_cd        text,
  cntrct_instt_nm        text,
  dmnd_instt_cd          text,
  dmnd_instt_nm          text,
  openg_date             date,
  data_bss_date          date,
  raw                    jsonb not null,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  primary key (cntrct_no, cntrct_ord)
);
create index contracts_corp_bizrno_idx on contracts (rprsnt_corp_bizrno);
create index contracts_bid_ntce_no_idx on contracts (bid_ntce_no);
create index contracts_cncls_date_idx  on contracts (cntrct_cncls_date desc);
create index contracts_corp_nm_trgm    on contracts using gin (rprsnt_corp_nm gin_trgm_ops);
create trigger trg_contracts_updated
  before update on contracts for each row execute function set_updated_at();


-- ====================================================================
-- 3. pre_specs : 사전규격 (SW 사업 식별 + 사양서 파일)
-- 소스: HrcspSsstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch
-- ====================================================================
create table pre_specs (
  bf_spec_rgst_no      text primary key,
  bid_ntce_no_list     text,
  prdct_clsfc_no_nm    text,
  bsns_div_nm          text,
  sw_biz_obj_yn        char(1),
  asign_bdgt_amt       bigint,
  rcpt_dt              timestamptz,
  rgst_dt              timestamptz,
  chg_dt               timestamptz,
  opnin_rgst_clse_dt   timestamptz,
  dlvr_daynum          int,
  order_instt_nm       text,
  rl_dminstt_nm        text,
  prdct_dtl_list       text,
  spec_doc_file_url_1  text,
  spec_doc_file_url_2  text,
  spec_doc_file_url_3  text,
  spec_doc_file_url_4  text,
  spec_doc_file_url_5  text,
  ref_no               text,
  raw                  jsonb not null,
  embedding            vector(1536),
  embedded_at          timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index pre_specs_sw_yn_idx     on pre_specs (sw_biz_obj_yn);
create index pre_specs_bsns_div_idx  on pre_specs (bsns_div_nm);
create index pre_specs_rgst_dt_idx   on pre_specs (rgst_dt desc);
create index pre_specs_embedding_idx on pre_specs using hnsw (embedding vector_cosine_ops);
create trigger trg_pre_specs_updated
  before update on pre_specs for each row execute function set_updated_at();


-- ====================================================================
-- 4. pre_spec_opinions : 사전규격 의견 ⭐ (회사 관심 신호 - 콜드스타트 해결)
-- 소스: HrcspSsstndrdInfoService/getPublicPrcureThngOpinionInfoServc
-- ====================================================================
create table pre_spec_opinions (
  bf_spec_rgst_no         text not null,
  opnin_no                text not null,
  ref_no                  text,
  opnin_titl              text,
  opnin_cntnts            text,
  mkng_corp_nm            text,
  mkr_nm                  text,
  mkr_email               text,
  mkr_tel                 text,
  inpt_dt                 timestamptz,
  rply_no                 text,
  spec_doc_opnin_file_url_1 text,
  raw                     jsonb not null,
  created_at              timestamptz not null default now(),
  primary key (bf_spec_rgst_no, opnin_no)
);
create index pre_spec_opinions_corp_idx     on pre_spec_opinions (mkng_corp_nm);
create index pre_spec_opinions_spec_idx     on pre_spec_opinions (bf_spec_rgst_no);
create index pre_spec_opinions_inpt_dt_idx  on pre_spec_opinions (inpt_dt desc);
create index pre_spec_opinions_corp_trgm    on pre_spec_opinions using gin (mkng_corp_nm gin_trgm_ops);


-- ====================================================================
-- 5. order_plans : 발주계획 (선행지표, "한 달 전 미리 안다" 차별화)
-- 소스: OrderPlanSttusService/getOrderPlanSttusListServcPPSSrch
-- ====================================================================
create table order_plans (
  order_plan_unty_no   text primary key,
  biz_nm               text,
  bsns_div_nm          text,
  bsns_ty_cd           text,
  bsns_ty_nm           text,
  order_year           text,
  order_mnth           text,
  cntrct_mthd_nm       text,
  prcrmnt_methd        text,
  order_instt_cd       text,
  order_instt_nm       text,
  totlmng_instt_nm     text,
  jrsdctn_div_nm       text,
  sum_order_amt        bigint,
  sum_order_dol_amt    numeric,
  bid_ntce_no_list     text,
  prdct_clsfc_no_nm    text,
  usg_cntnts           text,
  spec_cntnts          text,
  ntice_dt             timestamptz,
  chg_dt               timestamptz,
  raw                  jsonb not null,
  embedding            vector(1536),
  embedded_at          timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index order_plans_bsns_div_idx   on order_plans (bsns_div_nm);
create index order_plans_year_month_idx on order_plans (order_year, order_mnth);
create index order_plans_ntice_dt_idx   on order_plans (ntice_dt desc);
create index order_plans_embedding_idx  on order_plans using hnsw (embedding vector_cosine_ops);
create trigger trg_order_plans_updated
  before update on order_plans for each row execute function set_updated_at();


-- ====================================================================
-- 6. companies : 회사 마스터 (사업자번호 PK)
-- 소스: UsrInfoService02/getPrcrmntCorpBasicInfo02 + 계약 데이터 + 의견 작성업체명
-- ====================================================================
create table companies (
  bizrno              text primary key,
  corp_nm             text not null,
  english_nm          text,
  ceo_nm              text,
  opng_dt             date,
  rgn_cd              text,
  rgn_nm              text,
  zip_no              text,
  addr                text,
  dtl_addr            text,
  tel_no              text,
  fax_no              text,
  hmpg_addr           text,
  mnfctr_div_cd       text,
  mnfctr_div_nm       text,
  emp_count           int,
  corp_bsns_div_cd    text,
  corp_bsns_div_nm    text,
  hd_off_div_nm       text,
  unq_no_crtfct_yn    char(1),
  rgst_dt             timestamptz,
  -- 시그널 카운터 (집계 캐싱, 성능용)
  contract_count      int not null default 0,
  opinion_count       int not null default 0,
  award_participation_count int not null default 0,
  -- 부정당 제재 (UnptRsttCorpInfo02)
  is_restricted       boolean not null default false,
  restricted_until    date,
  -- 회사 벡터 (수주 + 관심 + 참여 시그널 통합 임베딩)
  embedding           vector(1536),
  embedded_at         timestamptz,
  raw                 jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index companies_corp_nm_idx       on companies (corp_nm);
create index companies_corp_nm_trgm      on companies using gin (corp_nm gin_trgm_ops);
create index companies_english_nm_trgm   on companies using gin (english_nm gin_trgm_ops);
create index companies_restricted_idx    on companies (is_restricted);
create index companies_embedding_idx     on companies using hnsw (embedding vector_cosine_ops);
create trigger trg_companies_updated
  before update on companies for each row execute function set_updated_at();


-- ====================================================================
-- 7. company_industries : 회사 보유 업종 (자격요건 매칭용)
-- 소스: UsrInfoService02/getPrcrmntCorpIndstrytyInfo02
-- ====================================================================
create table company_industries (
  bizrno              text not null references companies(bizrno) on delete cascade,
  indstryty_cd        text not null,
  indstryty_nm        text,
  rgst_dt             timestamptz,
  valid_to_dt         timestamptz,
  indstryty_sttus_nm  text,
  rprsnt_indstryty_yn char(1),
  raw                 jsonb,
  created_at          timestamptz not null default now(),
  primary key (bizrno, indstryty_cd)
);
create index company_industries_cd_idx on company_industries (indstryty_cd);


-- ====================================================================
-- 8. company_supply_products : 회사 공급물품
-- 소스: UsrInfoService02/getPrcrmntCorpSplyPrdctInfo02
-- ====================================================================
create table company_supply_products (
  bizrno               text not null references companies(bizrno) on delete cascade,
  dtl_prdct_clsfc_no   text not null,
  dtl_prdct_clsfc_nm   text,
  rgst_dt              timestamptz,
  rprsnt_prdct_yn      char(1),
  raw                  jsonb,
  created_at           timestamptz not null default now(),
  primary key (bizrno, dtl_prdct_clsfc_no)
);
create index company_supply_products_no_idx on company_supply_products (dtl_prdct_clsfc_no);


-- ====================================================================
-- 9. industries_baselaw : 업종-근거법규 매핑 (자격요건 lookup)
-- 소스: IndstrytyBaseLawrgltInfoService/getIndstrytyBaseLawrgltInfoList
-- ====================================================================
create table industries_baselaw (
  indstryty_cd     text primary key,
  indstryty_nm     text not null,
  baselaw_nm       text,
  baselaw_clause   text,
  raw              jsonb,
  updated_at       timestamptz not null default now()
);


-- ====================================================================
-- 10. award_results : 낙찰/개찰 결과 (회사 참여 시그널 ⭐)
-- 소스: ScsbidInfoService/getOpengResultListInfoOpengCompt
-- 참가한 모든 업체의 사업자번호 + 투찰금액 보존 → 수주 못한 회사도 추적
-- ====================================================================
create table award_results (
  bid_ntce_no            text not null,
  bid_ntce_ord           text not null,
  openg_rank             int not null,
  bizrno                 text,
  corp_nm                text,
  corp_ceo_nm            text,
  bid_amt                bigint,
  bid_rate               numeric,
  is_winner              boolean not null default false,
  openg_result_div_nm    text,   -- 낙찰/유찰/재입찰 등
  bsns_div_nm            text,
  raw                    jsonb not null,
  created_at             timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord, openg_rank)
);
create index award_results_bizrno_idx     on award_results (bizrno);
create index award_results_winner_idx     on award_results (is_winner) where is_winner = true;
create index award_results_corp_nm_trgm   on award_results using gin (corp_nm gin_trgm_ops);


-- ====================================================================
-- 11. subscribers : 이메일 알림 구독자 (락인)
-- ====================================================================
create table subscribers (
  id                uuid primary key default gen_random_uuid(),
  email             text not null unique,
  bizrno            text references companies(bizrno),
  corp_nm_input     text,
  verified_at       timestamptz,
  unsubscribed_at   timestamptz,
  created_at        timestamptz not null default now()
);
create index subscribers_bizrno_idx on subscribers (bizrno) where unsubscribed_at is null;


-- ====================================================================
-- 12. ingest_runs : 수집 잡 실행 로그
-- ====================================================================
create table ingest_runs (
  id              bigserial primary key,
  job_name        text not null,
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  rows_inserted   int default 0,
  rows_updated    int default 0,
  rows_failed     int default 0,
  status          text not null default 'running',
  error_msg       text,
  payload         jsonb
);
create index ingest_runs_job_started_idx on ingest_runs (job_name, started_at desc);
