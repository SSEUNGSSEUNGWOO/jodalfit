import "server-only";
import { unstable_cache } from "next/cache";
import { getServerSupabase } from "./supabase-server";
import { IS_KURE, rpcName } from "./embed-space";
import type { NoticeInsight } from "@/types/recommendations";
import { diffNoticeVersions, type Amendment, type NoticeVersion } from "./notice-diff";

export const SUMMARY_COLS =
  "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,dmnd_instt_nm,ntce_instt_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,bidprc_psbl_indstryty_nm,prtcpt_psbl_rgn_nm,cntrct_cncls_mthd_nm,rgn_lmt_yn";

export interface NoticeAttachment {
  seq: number;
  name: string | null;
  url: string;
}

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
  attachments: NoticeAttachment[] | null;
  /** 사전규격 등록번호 (0047) — 있으면 pre_specs 를 이걸로 직접 잇는다 */
  bf_spec_rgst_no: string | null;
  /** 입찰참가자격 등록 마감 (0047) — 입찰 마감보다 먼저 닫히는 데드라인 */
  bid_qlfct_rgst_dt: string | null;
  /** 발주계획 통합번호 (0051) — 있으면 order_plans 를 이걸로 직접 잇는다 */
  order_plan_unty_no: string | null;
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
  insight: NoticeInsight | null;
  /** 정정 이력 — 최신 정정이 앞. 원공고이거나 이전 차수가 DB에 없으면 빈 배열 */
  amendments: Amendment[];
  preSpecs: PreSpec[];
  opinions: PreSpecOpinion[];
  orderPlans: OrderPlan[];
  awards: Award[];
  contracts: Contract[];
}

/** 벡터 컬럼은 공간에 따라 다르다 — select 리터럴을 분기해야 supabase-js 타입 추론이 산다. */
const BID_NOTICE_COLUMNS = IS_KURE
  ? "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,ntce_instt_nm,dmnd_instt_nm,bidprc_psbl_indstryty_nm,bidwinr_dcsn_mthd_nm,cntrct_cncls_mthd_nm,bid_ntce_url,rgn_lmt_yn,prtcpt_psbl_rgn_nm,indstryty_lmt_yn,attachments,bf_spec_rgst_no,bid_qlfct_rgst_dt,order_plan_unty_no,embedding:embedding_k"
  : "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,ntce_instt_nm,dmnd_instt_nm,bidprc_psbl_indstryty_nm,bidwinr_dcsn_mthd_nm,cntrct_cncls_mthd_nm,bid_ntce_url,rgn_lmt_yn,prtcpt_psbl_rgn_nm,indstryty_lmt_yn,attachments,bf_spec_rgst_no,bid_qlfct_rgst_dt,order_plan_unty_no,embedding";

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

const PRE_SPEC_COLS =
  "bf_spec_rgst_no,prdct_clsfc_no_nm,bsns_div_nm,sw_biz_obj_yn,asign_bdgt_amt,rcpt_dt,rgst_dt,opnin_rgst_clse_dt,order_instt_nm,rl_dminstt_nm,spec_doc_file_url_1";
const ORDER_PLAN_COLS =
  "order_plan_unty_no,biz_nm,bsns_div_nm,bsns_ty_nm,order_year,order_mnth,cntrct_mthd_nm,order_instt_nm,sum_order_amt,ntice_dt";

export async function fetchLifecycle(
  bidNtceNo: string
): Promise<NoticeLifecycle | null> {
  const notice = await fetchBidNotice(bidNtceNo);
  if (!notice) return null;
  const c = getServerSupabase();

  // 5개 라이프사이클 단계 + 첨부문서 인사이트 + 정정 이력(정정 공고일 때만) 병렬 조회
  // 정렬은 전부 동률 없이 결정적으로 — 같은 데이터가 다른 순서로 렌더되면 ISR이 "바뀐 출력"으로 보고
  // 매번 다시 쓴다 (company.ts fetchCompanyProfile 주석 참조).
  const [insightRes, versionsRes, preSpecsRes, orderPlansRes, awardsRes, contractsRes] =
    await Promise.all([
      c
        .from("bid_notice_insights")
        .select("summary,scope,requirements,evaluation,schedule,keywords")
        .eq("bid_ntce_no", notice.bid_ntce_no)
        .eq("bid_ntce_ord", notice.bid_ntce_ord)
        .maybeSingle(),
      notice.bid_ntce_ord !== "000"
        ? c
            .from("bid_notices")
            .select(
              "bid_ntce_ord,bid_ntce_date,bid_ntce_nm,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,prtcpt_psbl_rgn_nm,bidprc_psbl_indstryty_nm,cntrct_cncls_mthd_nm,bidwinr_dcsn_mthd_nm,attachments"
            )
            .eq("bid_ntce_no", notice.bid_ntce_no)
            .order("bid_ntce_ord")
        : Promise.resolve({ data: null }),
      // 공고에 사전규격 등록번호(0047)가 있으면 그걸로 직접 잇는다. 없을 때만 예전 방식 —
      // 사전규격 쪽 공고번호 목록(bid_ntce_no_list)에 들어 있는지로 추측 (187건뿐이던 연결).
      notice.bf_spec_rgst_no
        ? c
            .from("pre_specs")
            .select(PRE_SPEC_COLS)
            .eq("bf_spec_rgst_no", notice.bf_spec_rgst_no)
            .limit(1)
        : c
            .from("pre_specs")
            .select(PRE_SPEC_COLS)
            .ilike("bid_ntce_no_list", `%${bidNtceNo}%`)
            .order("rgst_dt", { ascending: false, nullsFirst: false })
            .order("bf_spec_rgst_no")
            .limit(5),
      // 발주계획도 같은 구조(0051 order_plan_unty_no) — 직접 잇고, 없을 때만 공고번호 목록으로 추측.
      notice.order_plan_unty_no
        ? c
            .from("order_plans")
            .select(ORDER_PLAN_COLS)
            .eq("order_plan_unty_no", notice.order_plan_unty_no)
            .limit(1)
        : c
            .from("order_plans")
            .select(ORDER_PLAN_COLS)
            .ilike("bid_ntce_no_list", `%${bidNtceNo}%`)
            .order("ntice_dt", { ascending: false, nullsFirst: false })
            .order("order_plan_unty_no")
            .limit(5),
      c
        .from("award_results")
        .select(
          "bid_ntce_no,bid_ntce_ord,openg_rank,bizrno,corp_nm,bid_amt,bid_rate,is_winner"
        )
        .eq("bid_ntce_no", bidNtceNo)
        .order("openg_rank")
        .order("bizrno"),
      c
        .from("contracts")
        .select(
          "cntrct_no,cntrct_nm,cntrct_cncls_date,cntrct_amt,rprsnt_corp_nm,rprsnt_corp_bizrno"
        )
        .eq("bid_ntce_no", bidNtceNo)
        .order("cntrct_cncls_date", { ascending: false })
        .order("cntrct_no"),
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
      .order("inpt_dt", { ascending: false })
      .order("opnin_no");
    opinions = (opData as PreSpecOpinion[]) ?? [];
  }

  const awards = (awardsRes.data as Award[]) ?? [];
  const contracts = (contractsRes.data as Contract[]) ?? [];
  await redactOptoutCompanies(awards, contracts);

  return {
    notice,
    insight: (insightRes.data as NoticeInsight | null) ?? null,
    amendments: diffNoticeVersions((versionsRes.data as NoticeVersion[] | null) ?? []),
    preSpecs,
    opinions,
    orderPlans: (orderPlansRes.data as OrderPlan[]) ?? [],
    awards,
    contracts,
  };
}

const OPTOUT_LABEL = "비공개 요청 업체";

/** 비공개 요청 회사(0037)의 상호를 공고 페이지에서 가린다.
 *  회사 페이지를 내려도 award_results·contracts 는 companies 와 FK 가 없어
 *  여기서 따로 걸러주지 않으면 낙찰자·계약상대로 상호가 계속 노출된다. */
async function redactOptoutCompanies(
  awards: Award[],
  contracts: Contract[]
): Promise<void> {
  const norm = (v: string | null) => {
    const d = (v ?? "").replace(/\D/g, "");
    return d.length === 10 ? d : null;
  };
  const wanted = new Set<string>();
  for (const a of awards) {
    const n = norm(a.bizrno);
    if (n) wanted.add(n);
  }
  for (const t of contracts) {
    const n = norm(t.rprsnt_corp_bizrno);
    if (n) wanted.add(n);
  }
  if (wanted.size === 0) return;

  const { data } = await getServerSupabase()
    .from("companies")
    .select("bizrno_norm")
    .in("bizrno_norm", [...wanted])
    .not("optout_at", "is", null);
  const hidden = new Set(((data as { bizrno_norm: string }[]) ?? []).map((r) => r.bizrno_norm));
  if (hidden.size === 0) return;

  for (const a of awards) {
    const n = norm(a.bizrno);
    if (n && hidden.has(n)) {
      a.corp_nm = OPTOUT_LABEL;
      a.bizrno = null;
    }
  }
  for (const t of contracts) {
    const n = norm(t.rprsnt_corp_bizrno);
    if (n && hidden.has(n)) {
      t.rprsnt_corp_nm = OPTOUT_LABEL;
      t.rprsnt_corp_bizrno = null;
    }
  }
}

/** 비슷한 공고 — 해당 공고의 embedding을 기준으로 코사인 검색.
 *  자기 자신 + 같은 bid_ntce_no 다른 차수 제외, 마감 안 지난 것만.
 */
export interface SimilarNotice {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bsns_div_nm: string | null;
  dmnd_instt_nm: string | null;
  ntce_instt_nm: string | null;
  bid_clse_date: string | null;
  presmpt_prce: number | null;
  bidprc_psbl_indstryty_nm: string | null;
  similarity: number;
}

export async function fetchSimilarNotices(
  bidNtceNo: string,
  limit = 10
): Promise<SimilarNotice[]> {
  const c = getServerSupabase();
  // 1) source notice embedding 조회 (가장 최근 ord)
  const { data: src } = await c
    .from("bid_notices")
    .select(
      IS_KURE
        ? "bid_ntce_no,bid_ntce_ord,embedding:embedding_k"
        : "bid_ntce_no,bid_ntce_ord,embedding"
    )
    .eq("bid_ntce_no", bidNtceNo)
    .order("bid_ntce_ord", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!src?.embedding) return [];

  // 2) match_bid_notices RPC 호출 (오늘 이후 마감만)
  const today = new Date().toISOString().slice(0, 10);
  const candidatePool = limit * 4 + 5; // 자기 자신 제외 여유분
  const { data } = await c.rpc(rpcName("match_bid_notices"), {
    query_embedding: src.embedding,
    match_count: candidatePool,
    min_clse_date: today,
  });
  const rows = (data as (SimilarNotice & { bid_ntce_no: string })[]) ?? [];

  const seen = new Set<string>([bidNtceNo]); // 자기 자신
  const out: SimilarNotice[] = [];
  for (const r of rows) {
    if (!r.bid_ntce_no || seen.has(r.bid_ntce_no)) continue;
    seen.add(r.bid_ntce_no);
    out.push(r);
    if (out.length >= limit) break;
  }
  return out;
}

/** 인덱스 페이지용 — 진행 중 공고 (마감일 안 지남) */
export interface NoticeSummary {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bsns_div_nm: string | null;
  dmnd_instt_nm: string | null;
  ntce_instt_nm: string | null;
  bid_ntce_date: string | null;
  bid_clse_date: string | null;
  openg_date: string | null;
  presmpt_prce: number | null;
  asign_bdgt_amt: number | null;
  bidprc_psbl_indstryty_nm: string | null;
  prtcpt_psbl_rgn_nm: string | null;
  cntrct_cncls_mthd_nm: string | null;
  rgn_lmt_yn: string | null;
}

export type NoticeCategory =
  | "it"
  | "medical"
  | "construction"
  | "environment"
  | "education"
  | "consulting"
  | "other";

export const CATEGORY_LABELS: Record<NoticeCategory, string> = {
  it: "IT/소프트웨어",
  medical: "의료/보건",
  construction: "건설/토목",
  environment: "환경/시설",
  education: "교육/연구",
  consulting: "컨설팅/기획",
  other: "기타",
};

const CATEGORY_KEYWORDS: Record<Exclude<NoticeCategory, "other">, string[]> = {
  it: ["IT","소프트웨어","시스템","SI","전산","정보화","데이터","AI","인공지능","보안","클라우드","홈페이지","웹","앱","어플리케이션","네트워크","서버","DB","GIS","BIM","메타버스","블록체인","챗봇","디지털"],
  medical: ["병원","의약품","의료","보건","진료","약품","보건소","요양","간호","임상","백신","진단","의료기기"],
  construction: ["공사","건축","토목","도로","상수도","하수도","관로","정비공사","신축","증축","개축","리모델링","포장","교량","터널","댐","준설","아스콘"],
  environment: ["환경","청소","미화","경비","재활용","폐기물","정수","수처리","오염","대기","수질","조경","녹지","공원","시설관리","유지관리"],
  education: ["교육","학교","대학","학술","연구","연구용역","교과서","학습","캠퍼스","강의","학원","교과","학생","교육청"],
  consulting: ["컨설팅","기획","조사","전략","정책","분석","마스터플랜","평가","자문","감리","설계용역"],
};

/** 한 공고가 속한 카테고리들을 반환 (여러 개 가능, 매칭 0개면 ["other"]). */
export function categoriesOf(notice: {
  bid_ntce_nm?: string | null;
  bidprc_psbl_indstryty_nm?: string | null;
  bsns_div_nm?: string | null;
}): NoticeCategory[] {
  const text = [
    notice.bid_ntce_nm,
    notice.bidprc_psbl_indstryty_nm,
    notice.bsns_div_nm,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const hits: NoticeCategory[] = [];
  for (const [cat, kws] of Object.entries(CATEGORY_KEYWORDS) as [
    Exclude<NoticeCategory, "other">,
    string[],
  ][]) {
    if (kws.some((kw) => text.includes(kw.toLowerCase()))) {
      hits.push(cat);
    }
  }
  return hits.length > 0 ? hits : ["other"];
}

export interface NoticeFilters {
  bsnsDiv?: string;
  dday?: 7 | 14 | 30; // D-day 이내 (없으면 전체)
  priceBucket?: "lt1" | "1to10" | "10to50" | "gt50";
  rgn?: string; // 시·도 키워드 (예: "서울")
  category?: NoticeCategory;
  sort?: "close" | "price_desc" | "ntce_desc";
}

const PRICE_RANGES: Record<NonNullable<NoticeFilters["priceBucket"]>, [number, number | null]> = {
  lt1: [0, 100_000_000],
  "1to10": [100_000_000, 1_000_000_000],
  "10to50": [1_000_000_000, 5_000_000_000],
  gt50: [5_000_000_000, null],
};

/** Supabase 빌더에서 쓰는 메서드만 — 구체 타입(PostgrestFilterBuilder 의 7개 제네릭)에 묶이지 않게. */
interface FilterChain<T> {
  gte(column: string, value: unknown): T;
  lte(column: string, value: unknown): T;
  lt(column: string, value: unknown): T;
  eq(column: string, value: unknown): T;
  ilike(column: string, pattern: string): T;
}

interface OrderChain<T> {
  order(column: string, options?: { ascending?: boolean; nullsFirst?: boolean }): T;
}

function applyFilters<T extends FilterChain<T>>(
  q: T,
  today: string,
  f: NoticeFilters
): T {
  let qq = q.gte("bid_clse_date", today);
  if (f.bsnsDiv) qq = qq.eq("bsns_div_nm", f.bsnsDiv);
  if (f.dday) {
    const max = new Date();
    max.setHours(0, 0, 0, 0);
    max.setDate(max.getDate() + f.dday);
    qq = qq.lte("bid_clse_date", max.toISOString().slice(0, 10));
  }
  if (f.priceBucket) {
    const [lo, hi] = PRICE_RANGES[f.priceBucket];
    qq = qq.gte("presmpt_prce", lo);
    if (hi != null) qq = qq.lt("presmpt_prce", hi);
  }
  if (f.rgn) {
    // 시·도 키워드 부분 일치 (예: "서울" → "서울특별시 …")
    qq = qq.ilike("prtcpt_psbl_rgn_nm", `%${f.rgn}%`);
  }
  return qq;
}

function orderClause<T extends OrderChain<T>>(q: T, sort: NoticeFilters["sort"]): T {
  switch (sort) {
    case "price_desc":
      return q.order("presmpt_prce", { ascending: false, nullsFirst: false });
    case "close":
      return q.order("bid_clse_date");
    // 기본 신규순 — 마감 임박순이 기본이면 첫 화면이 D-1 일색이라 "늦은 공고만 있다" 인상을 줌
    case "ntce_desc":
    default:
      return q.order("bid_ntce_date", { ascending: false, nullsFirst: false });
  }
}

/** 조건 검색(0050 search_bid_notices) — 키워드·발주기관·업종·물품코드까지. 페이지는 아직 fetchBrowsePage 를 쓴다. */
export interface SearchFilters {
  /** 키워드 — 제목 우선, 3글자 이상이면 첨부 요약·키워드도. 2글자는 제목만 */
  q?: string;
  bsnsDiv?: string;
  /** 참가가능지역 부분 일치 — NoticeFilters.rgn 과 같은 뜻(지역 제한 없는 공고는 안 잡힘) */
  rgn?: string;
  /** 발주기관 — 수요기관·공고기관 부분 일치 */
  instt?: string;
  /** 추정가 [min, max) 원 */
  prcMin?: number;
  prcMax?: number;
  /** 마감일 구간 (YYYY-MM-DD). clseFrom 없으면 오늘부터 */
  clseFrom?: string;
  clseTo?: string;
  /** 입찰참가가능업종명 부분 일치 (회사 통로 0044 와 같은 규칙) */
  industry?: string;
  /** 물품분류번호 10자리 (0047 prdct_clsfc_nos 포함) */
  prdctCode?: string;
  sort?: "close" | "price_desc" | "ntce_desc";
  limit?: number;
  offset?: number;
}

/** search_bid_notices 응답 행 — match_bid_notices 와 같은 컬럼 + title_hit·total_count */
export interface SearchedNotice {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bsns_div_nm: string | null;
  bid_ntce_date: string | null;
  bid_clse_date: string | null;
  openg_date: string | null;
  presmpt_prce: number | null;
  ntce_instt_nm: string | null;
  dmnd_instt_nm: string | null;
  bidprc_psbl_indstryty_nm: string | null;
  rgn_lmt_yn: string | null;
  prtcpt_psbl_rgn_nm: string | null;
  indstryty_lmt_yn: string | null;
  bid_ntce_url: string | null;
  /** 키워드가 제목에 걸렸으면 true, 요약·키워드에만 걸렸으면 false. 키워드 없으면 false */
  title_hit: boolean;
  /** 필터에 맞는 전체 건수 (모든 행에 같은 값) */
  total_count: number;
}

export async function searchNotices(
  filters: SearchFilters = {}
): Promise<{ rows: SearchedNotice[]; totalCount: number }> {
  const c = getServerSupabase();
  const { data, error } = await c.rpc("search_bid_notices", {
    q: filters.q ?? null,
    bsns_div: filters.bsnsDiv ?? null,
    rgn: filters.rgn ?? null,
    instt: filters.instt ?? null,
    prc_min: filters.prcMin ?? null,
    prc_max: filters.prcMax ?? null,
    clse_from: filters.clseFrom ?? null,
    clse_to: filters.clseTo ?? null,
    industry: filters.industry ?? null,
    prdct_code: filters.prdctCode ?? null,
    lim: filters.limit ?? 50,
    off: filters.offset ?? 0,
    sort: filters.sort ?? "close",
  });
  if (error) throw new Error(`search_bid_notices: ${error.message}`);
  const rows = (data as SearchedNotice[] | null) ?? [];
  return { rows, totalCount: rows[0]?.total_count ?? 0 };
}

/** /about 데이터 규모 — 큰 테이블은 estimated(pg_class.reltuples)로, 1시간 캐시. */
export interface AboutStats {
  activeNotices: number;
  totalNotices: number;
  companies: number;
  contracts: number;
}
export const fetchAboutStats = unstable_cache(
  async (): Promise<AboutStats> => {
    const c = getServerSupabase();
    const est = (table: string) =>
      c.from(table).select("*", { count: "estimated", head: true });
    const [active, notices, companies, contracts] = await Promise.all([
      fetchActiveNoticesRoughCount(),
      est("bid_notices"),
      est("companies"),
      est("contracts"),
    ]);
    return {
      activeNotices: active,
      totalNotices: notices.count ?? 0,
      companies: companies.count ?? 0,
      contracts: contracts.count ?? 0,
    };
  },
  ["about-stats"],
  { revalidate: 3600 }
);

/** 빠른 active 공고 카운트 (dedupe 없는 raw row count, head only). 홈 화면 신뢰 신호용. */
export async function fetchActiveNoticesRoughCount(): Promise<number> {
  const c = getServerSupabase();
  const today = new Date().toISOString().slice(0, 10);
  const { count } = await c
    .from("bid_notices")
    .select("bid_ntce_no", { count: "exact", head: true })
    .gte("bid_clse_date", today);
  return count ?? 0;
}

/** 한 번 fetch로 카테고리 분류·필터·페이지네이션 모두 처리.
 *  카테고리 필터는 DB로 못 거니까(키워드 OR 사전 60개+) 메모리에서 처리.
 *  fetchBrowseNoticesCount와 fetchBrowseNotices를 통합한 형태.
 */
export interface BrowsePage {
  rows: NoticeSummary[];
  totalCount: number;
  categoryCounts: Record<NoticeCategory, number>;
}

/** 카테고리 카운트 — 활성 공고 전체 기준, 다른 필터는 적용 안 함.
 *  unstable_cache로 1시간 캐싱. 사용자 필터 조합과 무관해서 cache key 단일.
 *  UX: 필터 켜도 카테고리 탭 숫자는 전체 기준으로 표시 (정밀 카운트는 옵션 B로 후속). */
const fetchCategoryCountsCached = unstable_cache(
  async (): Promise<Record<NoticeCategory, number>> => {
    const c = getServerSupabase();
    const today = new Date().toISOString().slice(0, 10);
    const counts: Record<NoticeCategory, number> = {
      it: 0,
      medical: 0,
      construction: 0,
      environment: 0,
      education: 0,
      consulting: 0,
      other: 0,
    };
    const seen = new Set<string>();
    const PAGE = 1000;
    let offset = 0;
    while (true) {
      const { data } = await c
        .from("bid_notices")
        .select("bid_ntce_no,bid_ntce_nm,bidprc_psbl_indstryty_nm,bsns_div_nm")
        .gte("bid_clse_date", today)
        .range(offset, offset + PAGE - 1);
      const rows = (data as Array<Parameters<typeof categoriesOf>[0] & { bid_ntce_no: string }>) ?? [];
      if (rows.length === 0) break;
      for (const r of rows) {
        if (!r.bid_ntce_no || seen.has(r.bid_ntce_no)) continue;
        seen.add(r.bid_ntce_no);
        for (const cat of categoriesOf(r)) counts[cat]++;
      }
      if (rows.length < PAGE) break;
      offset += PAGE;
      if (offset > 500000) break;
    }
    return counts;
  },
  ["notice-category-counts-v1"],
  { revalidate: 3600 }
);

export async function fetchBrowsePage(
  filters: NoticeFilters = {},
  page = 1,
  pageSize = 100
): Promise<BrowsePage> {
  // 카테고리 필터 있을 때만 메모리 분류 위해 풀 fetch (느린 경로)
  if (filters.category) {
    return fetchBrowsePageWithCategory(filters, page, pageSize);
  }

  // Fast path: 카테고리 필터 없으면 페이지 깊이만큼만 fetch
  const c = getServerSupabase();
  const today = new Date().toISOString().slice(0, 10);

  const countPromise = (async () => {
    let q = c.from("bid_notices").select("bid_ntce_no", {
      count: "exact",
      head: true,
    });
    q = applyFilters(q, today, filters);
    return q;
  })();

  const listPromise = (async () => {
    const target = page * pageSize + pageSize; // 깊이 + 한 페이지 여유
    const collected: NoticeSummary[] = [];
    const seen = new Set<string>();
    const PAGE = 1000;
    let offset = 0;
    while (collected.length < target) {
      let q = c.from("bid_notices").select(SUMMARY_COLS);
      q = applyFilters(q, today, filters);
      q = orderClause(q, filters.sort);
      q = q.range(offset, offset + PAGE - 1);
      const { data } = await q;
      const rows = (data as NoticeSummary[]) ?? [];
      if (rows.length === 0) break;
      for (const r of rows) {
        if (!r.bid_ntce_no || seen.has(r.bid_ntce_no)) continue;
        seen.add(r.bid_ntce_no);
        collected.push(r);
      }
      if (rows.length < PAGE) break;
      offset += PAGE;
      if (offset > 500000) break;
    }
    const start = (page - 1) * pageSize;
    return collected.slice(start, start + pageSize);
  })();

  const [{ count: totalCount }, rows, categoryCounts] = await Promise.all([
    countPromise,
    listPromise,
    fetchCategoryCountsCached(),
  ]);

  return {
    rows,
    totalCount: totalCount ?? 0,
    categoryCounts,
  };
}

/** 카테고리 필터가 있을 때만 사용: 메모리 분류를 위해 활성 공고 풀을 모두 fetch. */
async function fetchBrowsePageWithCategory(
  filters: NoticeFilters,
  page: number,
  pageSize: number
): Promise<BrowsePage> {
  const c = getServerSupabase();
  const today = new Date().toISOString().slice(0, 10);
  const PAGE = 1000;

  const collected: NoticeSummary[] = [];
  const seen = new Set<string>();
  let offset = 0;
  while (true) {
    let q = c.from("bid_notices").select(SUMMARY_COLS);
    q = applyFilters(q, today, filters);
    q = orderClause(q, filters.sort);
    q = q.range(offset, offset + PAGE - 1);
    const { data } = await q;
    const rows = (data as NoticeSummary[]) ?? [];
    if (rows.length === 0) break;
    for (const r of rows) {
      if (!r.bid_ntce_no || seen.has(r.bid_ntce_no)) continue;
      seen.add(r.bid_ntce_no);
      collected.push(r);
    }
    if (rows.length < PAGE) break;
    offset += PAGE;
    if (offset > 500000) break;
  }

  const filtered = collected.filter((r) =>
    categoriesOf(r).includes(filters.category!)
  );
  const start = (page - 1) * pageSize;
  const rows = filtered.slice(start, start + pageSize);

  const categoryCounts = await fetchCategoryCountsCached();

  return {
    rows,
    totalCount: filtered.length,
    categoryCounts,
  };
}
