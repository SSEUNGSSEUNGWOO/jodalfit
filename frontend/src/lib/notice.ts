import "server-only";
import { getServerSupabase } from "./supabase-server";

export interface BidNotice {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bsns_div_nm: string | null;
  bid_ntce_date: string | null;
  bid_clse_date: string | null;
  openg_date: string | null;
  presmpt_prce: number | null;
  asign_bdgt_amt: number | null;
  ntce_instt_nm: string | null;
  dmnd_instt_nm: string | null;
  bidprc_psbl_indstryty_nm: string | null;
  bidwinr_dcsn_mthd_nm: string | null;
  cntrct_cncls_mthd_nm: string | null;
  bid_ntce_url: string | null;
  rgn_lmt_yn: string | null;
  prtcpt_psbl_rgn_nm: string | null;
  indstryty_lmt_yn: string | null;
  has_embedding: boolean;
}

export interface PreSpec {
  bf_spec_rgst_no: string;
  prdct_clsfc_no_nm: string | null;
  bsns_div_nm: string | null;
  sw_biz_obj_yn: string | null;
  asign_bdgt_amt: number | null;
  rcpt_dt: string | null;
  rgst_dt: string | null;
  opnin_rgst_clse_dt: string | null;
  order_instt_nm: string | null;
  rl_dminstt_nm: string | null;
  spec_doc_file_url_1: string | null;
}

export interface PreSpecOpinion {
  bf_spec_rgst_no: string;
  opnin_no: string;
  opnin_titl: string | null;
  opnin_cntnts: string | null;
  mkng_corp_nm: string | null;
  mkr_nm: string | null;
  inpt_dt: string | null;
}

export interface OrderPlan {
  order_plan_unty_no: string;
  biz_nm: string | null;
  bsns_div_nm: string | null;
  bsns_ty_nm: string | null;
  order_year: string | null;
  order_mnth: string | null;
  cntrct_mthd_nm: string | null;
  order_instt_nm: string | null;
  sum_order_amt: number | null;
  ntice_dt: string | null;
}

export interface Award {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  openg_rank: number;
  bizrno: string | null;
  corp_nm: string | null;
  corp_ceo_nm: string | null;
  bid_amt: number | null;
  bid_rate: number | null;
  is_winner: boolean;
}

export interface Contract {
  cntrct_no: string;
  cntrct_nm: string | null;
  cntrct_cncls_date: string | null;
  cntrct_amt: number | null;
  rprsnt_corp_nm: string | null;
  rprsnt_corp_bizrno: string | null;
}

export interface NoticeLifecycle {
  notice: BidNotice;
  preSpecs: PreSpec[];
  opinions: PreSpecOpinion[];
  orderPlans: OrderPlan[];
  awards: Award[];
  contracts: Contract[];
}

const BID_NOTICE_COLUMNS =
  "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,ntce_instt_nm,dmnd_instt_nm,bidprc_psbl_indstryty_nm,bidwinr_dcsn_mthd_nm,cntrct_cncls_mthd_nm,bid_ntce_url,rgn_lmt_yn,prtcpt_psbl_rgn_nm,indstryty_lmt_yn,embedding";

export async function fetchBidNotice(
  bidNtceNo: string
): Promise<BidNotice | null> {
  const c = getServerSupabase();
  const { data } = await c
    .from("bid_notices")
    .select(BID_NOTICE_COLUMNS)
    .eq("bid_ntce_no", bidNtceNo)
    .order("bid_ntce_ord", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!data) return null;
  const { embedding, ...rest } = data as Record<string, unknown>;
  return {
    ...(rest as Omit<BidNotice, "has_embedding">),
    has_embedding: !!embedding,
  };
}

export async function fetchLifecycle(
  bidNtceNo: string
): Promise<NoticeLifecycle | null> {
  const notice = await fetchBidNotice(bidNtceNo);
  if (!notice) return null;
  const c = getServerSupabase();

  // 5개 라이프사이클 단계 병렬 조회
  const [preSpecsRes, orderPlansRes, awardsRes, contractsRes] =
    await Promise.all([
      c
        .from("pre_specs")
        .select(
          "bf_spec_rgst_no,prdct_clsfc_no_nm,bsns_div_nm,sw_biz_obj_yn,asign_bdgt_amt,rcpt_dt,rgst_dt,opnin_rgst_clse_dt,order_instt_nm,rl_dminstt_nm,spec_doc_file_url_1"
        )
        .ilike("bid_ntce_no_list", `%${bidNtceNo}%`)
        .limit(5),
      c
        .from("order_plans")
        .select(
          "order_plan_unty_no,biz_nm,bsns_div_nm,bsns_ty_nm,order_year,order_mnth,cntrct_mthd_nm,order_instt_nm,sum_order_amt,ntice_dt"
        )
        .ilike("bid_ntce_no_list", `%${bidNtceNo}%`)
        .limit(5),
      c
        .from("award_results")
        .select(
          "bid_ntce_no,bid_ntce_ord,openg_rank,bizrno,corp_nm,corp_ceo_nm,bid_amt,bid_rate,is_winner"
        )
        .eq("bid_ntce_no", bidNtceNo)
        .order("openg_rank"),
      c
        .from("contracts")
        .select(
          "cntrct_no,cntrct_nm,cntrct_cncls_date,cntrct_amt,rprsnt_corp_nm,rprsnt_corp_bizrno"
        )
        .eq("bid_ntce_no", bidNtceNo)
        .order("cntrct_cncls_date", { ascending: false }),
    ]);

  const preSpecs = (preSpecsRes.data as PreSpec[]) ?? [];

  // 사전규격 의견은 사전규격 등록번호로 조회
  let opinions: PreSpecOpinion[] = [];
  if (preSpecs.length > 0) {
    const specIds = preSpecs.map((s) => s.bf_spec_rgst_no);
    const { data: opData } = await c
      .from("pre_spec_opinions")
      .select(
        "bf_spec_rgst_no,opnin_no,opnin_titl,opnin_cntnts,mkng_corp_nm,mkr_nm,inpt_dt"
      )
      .in("bf_spec_rgst_no", specIds)
      .order("inpt_dt", { ascending: false });
    opinions = (opData as PreSpecOpinion[]) ?? [];
  }

  return {
    notice,
    preSpecs,
    opinions,
    orderPlans: (orderPlansRes.data as OrderPlan[]) ?? [],
    awards: (awardsRes.data as Award[]) ?? [],
    contracts: (contractsRes.data as Contract[]) ?? [],
  };
}

/** sitemap용 — 최근 입찰공고 목록 */
export async function fetchRecentNoticesForSitemap(
  limit = 5000
): Promise<{ bid_ntce_no: string; updated_at: string }[]> {
  const c = getServerSupabase();
  const { data } = await c
    .from("bid_notices")
    .select("bid_ntce_no,updated_at")
    .order("bid_ntce_date", { ascending: false })
    .limit(limit);
  return (data as { bid_ntce_no: string; updated_at: string }[]) ?? [];
}

/** 인덱스 페이지용 — 진행 중 공고 (마감일 안 지남) */
export interface NoticeSummary {
  bid_ntce_no: string;
  bid_ntce_nm: string;
  bsns_div_nm: string | null;
  dmnd_instt_nm: string | null;
  bid_clse_date: string | null;
  presmpt_prce: number | null;
}

export async function fetchBrowseNotices(
  limit = 30,
  bsnsDiv?: string
): Promise<NoticeSummary[]> {
  const c = getServerSupabase();
  const today = new Date().toISOString().slice(0, 10);
  let query = c
    .from("bid_notices")
    .select(
      "bid_ntce_no,bid_ntce_nm,bsns_div_nm,dmnd_instt_nm,bid_clse_date,presmpt_prce"
    )
    .gte("bid_clse_date", today)
    .order("bid_clse_date")
    .limit(limit);
  if (bsnsDiv) query = query.eq("bsns_div_nm", bsnsDiv);
  const { data } = await query;
  return (data as NoticeSummary[]) ?? [];
}
