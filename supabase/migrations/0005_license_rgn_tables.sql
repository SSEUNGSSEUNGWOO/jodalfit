-- 자격필터 강화 테이블 (Phase 2b)
-- bid_notices와 1:N 관계 (한 공고에 여러 면허/지역 제한)

create table bid_license_limits (
  bid_ntce_no   text not null,
  bid_ntce_ord  text not null,
  lmt_grp_no    text not null,
  lmt_sno       text not null,
  bsns_div_nm   text,
  lcns_lmt_nm   text,                      -- "소프트웨어사업자(컴퓨터관련서비스사업)/1468"
  permsn_indstryty_list text,
  indstryty_mfrc_fld_list text,
  rgst_dt       timestamptz,
  raw           jsonb not null,
  created_at    timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord, lmt_grp_no, lmt_sno)
);
create index bid_license_limits_ntce_idx on bid_license_limits (bid_ntce_no, bid_ntce_ord);
create index bid_license_limits_lcns_idx on bid_license_limits (lcns_lmt_nm);
create index bid_license_limits_lcns_trgm on bid_license_limits using gin (lcns_lmt_nm gin_trgm_ops);


create table bid_rgn_limits (
  bid_ntce_no       text not null,
  bid_ntce_ord      text not null,
  lmt_sno           text not null,
  bsns_div_nm       text,
  prtcpt_psbl_rgn_nm text,
  rgst_dt           timestamptz,
  raw               jsonb not null,
  created_at        timestamptz not null default now(),
  primary key (bid_ntce_no, bid_ntce_ord, lmt_sno)
);
create index bid_rgn_limits_ntce_idx on bid_rgn_limits (bid_ntce_no, bid_ntce_ord);
create index bid_rgn_limits_rgn_idx  on bid_rgn_limits (prtcpt_psbl_rgn_nm);
