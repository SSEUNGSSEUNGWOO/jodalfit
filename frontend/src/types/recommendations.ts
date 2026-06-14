export interface CompanyDigest {
  bizrno: string;
  corp_nm: string;
  rgn_nm?: string;
  corp_bsns_div_nm?: string;
}

export type RecommendationStage = "notice" | "pre_spec" | "order_plan";

export interface BidRecommendation {
  stage?: "notice";
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bsns_div_nm: string;
  bid_ntce_date: string | null;
  bid_clse_date: string | null;
  openg_date?: string | null;
  presmpt_prce: number | null;
  ntce_instt_nm: string | null;
  dmnd_instt_nm: string | null;
  bidprc_psbl_indstryty_nm: string | null;
  prtcpt_psbl_rgn_nm: string | null;
  bid_ntce_url: string | null;
  base_similarity: number;
  bonus: number;
  score: number;
  explanation?: string;
  evidence?: string[];
}

/** 사전규격(골든타임) 매칭. 의견 마감일(opnin_rgst_clse_dt)이 핵심 */
export interface PreSpecRecommendation {
  stage?: "pre_spec";
  bf_spec_rgst_no: string;
  bid_ntce_no_list: string | null;
  prdct_clsfc_no_nm: string | null;
  bsns_div_nm: string | null;
  sw_biz_obj_yn: string | null;
  asign_bdgt_amt: number | null;
  rgst_dt: string | null;
  opnin_rgst_clse_dt: string | null;
  order_instt_nm: string | null;
  rl_dminstt_nm: string | null;
  prdct_dtl_list: string | null;
  ref_no: string | null;
  base_similarity: number;
  score: number;
}

/** 발주계획(선행지표). 사양 미확정, 연/월만 표시 */
export interface OrderPlanRecommendation {
  stage?: "order_plan";
  order_plan_unty_no: string;
  biz_nm: string | null;
  bsns_div_nm: string | null;
  bsns_ty_nm: string | null;
  order_year: string | null;
  order_mnth: string | null;
  cntrct_mthd_nm: string | null;
  order_instt_nm: string | null;
  totlmng_instt_nm: string | null;
  sum_order_amt: number | null;
  prdct_clsfc_no_nm: string | null;
  usg_cntnts: string | null;
  spec_cntnts: string | null;
  ntice_dt: string | null;
  base_similarity: number;
  score: number;
}

export interface VizAnchor {
  key: string;
  label: string;
  x: number;
  y: number;
}
export interface VizResultPoint {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  x: number;
  y: number;
  score: number;
  bid_ntce_nm: string | null;
}
export interface VizData {
  anchors: VizAnchor[];
  company: { x: number; y: number };
  results: VizResultPoint[];
}

export interface RecommendationResponse {
  company: CompanyDigest | null;
  results: BidRecommendation[];
  /** v0.3 사전규격 매칭 (골든타임) */
  pre_spec_results?: PreSpecRecommendation[];
  /** v0.3 발주계획 매칭 (선행지표) */
  order_plan_results?: OrderPlanRecommendation[];
  /** v0.3 회사+키워드 하이브리드 시 입력된 키워드 echo */
  keywords?: string | null;
  /** v0.4 임베딩 공간 시각화 — anchor 기반 좌표 */
  viz?: VizData | null;
  error?: string | null;
  mode?: "company" | "keywords" | "auto";
  query?: string;
  /** "keywords"면 회사 벡터 없거나 식별 실패 — 프론트가 키워드 폴백 UI 노출 */
  fallback?: "keywords";
  /** auto 모드 — 회사 매칭과 키워드 매칭 중 어느 쪽을 메인 탭으로 띄울지 */
  primary?: "company" | "keywords";
  /** auto 모드 — 키워드 매칭 결과 (메인이 company여도 함께 노출) */
  keyword_query?: string;
  keyword_results?: BidRecommendation[];
}
