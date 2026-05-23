export interface CompanyDigest {
  bizrno: string;
  corp_nm: string;
  rgn_nm?: string;
  corp_bsns_div_nm?: string;
}

export interface BidRecommendation {
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

export interface RecommendationResponse {
  company: CompanyDigest | null;
  results: BidRecommendation[];
  error?: string;
}
