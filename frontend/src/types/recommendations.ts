export interface CompanyDigest {
  bizrno: string;
  corp_nm: string;
  rgn_nm?: string;
  corp_bsns_div_nm?: string;
  /** 나라장터 등록업종 수. 0 이면 면허 자격을 판정하지 못한 회사(백엔드 recommend.py). 캐시된 옛 응답에는 없다. */
  industry_count?: number;
  /** 어떤 길로 찾았나(백엔드 find_company). fuzzy = 오타 등급으로만 잡힌 회사 — 다른 회사일 수 있어 화면이 그 사실을 적는다. 2026-10-27 */
  match?: "bizrno" | "exact" | "partial" | "fuzzy";
}

export type RecommendationStage = "notice" | "pre_spec" | "order_plan";

/** 첨부문서(제안요청서 등)에서 LLM으로 구조화한 공고 인사이트 (bid_notice_insights) */
export interface NoticeInsight {
  summary: string | null;
  scope: string[] | null;
  requirements:
    | {
        kind: "license" | "certification" | "performance" | "region" | "company_size" | "other";
        text: string;
        mandatory: boolean;
      }[]
    | null;
  evaluation: {
    method: string | null;
    technical_pct: number | null;
    price_pct: number | null;
    presentation: boolean | null;
    note: string | null;
  } | null;
  /** 문서에 적힌 표현 그대로 (날짜 정규화 없음). 2026-09-01 이후 요약분부터 채워짐 */
  schedule: {
    start: string | null;
    end: string | null;
    duration: string | null;
    delivery_deadline: string | null;
  } | null;
  keywords: string[] | null;
}

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
  /** v2 — 가중치 합산 raw 점수 (score는 표시용 0~1 정규화) */
  score_raw?: number;
  /** v2 — 시그널별 라벨·점수. label은 그대로 배지가 됨 */
  score_breakdown?: ScoreSignal[];
  /** v2 — 자격 하드필터 판정 상세 */
  qualification?: {
    passed: boolean;
    unverified: boolean;
    reasons: string[];
    failures: string[];
  };
  /** 첨부문서 인사이트 — 문서가 없거나 아직 요약 전이면 없음 */
  insight?: NoticeInsight;
}

/** 키워드 모드 — 제목에 검색어 낱말이 전부 든 진행 공고(전부, 마감 가까운 순). 순위·점수가 없다(backend title_match.py). */
export type TitleMatch = Pick<BidRecommendation,
  "stage" | "bid_ntce_no" | "bid_ntce_ord" | "bid_ntce_nm" | "bsns_div_nm" | "bid_ntce_date" | "bid_clse_date" | "openg_date"
  | "presmpt_prce" | "ntce_instt_nm" | "dmnd_instt_nm" | "bidprc_psbl_indstryty_nm" | "prtcpt_psbl_rgn_nm" | "bid_ntce_url"> & {
  /** 제목에 없는 낱말이 어디서 맞았는가(기관 = 수요·공고기관명, 지역 = 참가 가능 지역). 제목에 다 있으면 빈 목록. 2026-10-28 */
  matched_in?: ("기관" | "지역")[];
};

/** 키워드 모드 좁히기 — URL `div`·`due` 와 스트림 본문이 같은 값을 쓴다 */
export type KeywordFilter = { div: "물품" | "용역" | "공사" | null; due: 7 | 30 | null };

/** v2 랭킹 시그널 1건 — 가산/감산 근거 */
export interface ScoreSignal {
  key: string;
  label: string;
  points: number;
  [extra: string]: unknown;
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
  /** 키워드 모드 — 제목 일치 전부(상한 300). results 에는 이 공고들이 빠져 있다(같은 공고가 두 판에 안 보이게). 2026-10-27 */
  title_matches?: TitleMatch[];
  /** 제목 일치가 300건을 넘어 마감 가까운 300건만 실었다 */
  title_match_capped?: boolean;
  /** 제목 일치에 쓴 낱말(질의를 쪼갠 것, 전부 포함 조건) */
  title_terms?: string[];
  /** v0.3 사전규격 매칭 (골든타임) */
  pre_spec_results?: PreSpecRecommendation[];
  /** v0.3 발주계획 매칭 (선행지표) */
  order_plan_results?: OrderPlanRecommendation[];
  /** v0.3 회사+키워드 하이브리드 시 입력된 키워드 echo */
  keywords?: string | null;
  /** v0.4 임베딩 공간 시각화 — anchor 기반 좌표 */
  viz?: VizData | null;
  /** v2 회사 모드 — 카드별 설명 대신 LLM 상단 요약 1회 */
  summary?: string;
  error?: string | null;
  mode?: "company" | "keywords" | "auto";
  /** A/B — 이 응답을 만든 랭킹 알고리즘 */
  algorithm?: "v1" | "v2";
  query?: string;
  /** "keywords"면 회사 벡터 없거나 식별 실패 — 프론트가 키워드 폴백 UI 노출 */
  fallback?: "keywords";
  /** auto 모드 — 회사 매칭과 키워드 매칭 중 어느 쪽을 메인 탭으로 띄울지 */
  primary?: "company" | "keywords";
  /** auto 모드 — 키워드 매칭 결과 (메인이 company여도 함께 노출) */
  keyword_query?: string;
  keyword_results?: BidRecommendation[];
  /** v2 스트림 — funnel 단계 카운트 (키워드 모드 등 스트림 미사용 시 없음) */
  funnel?: FunnelCounts | null;
}

// 0057: industry(등록업종 허용 공고 수)를 뺐다 — 깔때기의 칸이 아니었다(Scene.tsx 주석 참조).
export type FunnelCounts = { total: number };

export type StreamEvent =
  | { type: "funnel"; total: number }
  | { type: "stage"; stage: "search"; candidates: number }
  | { type: "stage"; stage: "qualify"; candidates: number; passed: number }
  | { type: "stage"; stage: "rank"; results: number }
  | { type: "results"; data: RecommendationResponse }
  | { type: "summary"; text: string; error?: string }
  | { type: "explanation"; scope: "primary" | "keyword"; bid_ntce_no: string; bid_ntce_ord: string; text: string }
  | { type: "error"; message: string; status?: number }
  | { type: "done" };
