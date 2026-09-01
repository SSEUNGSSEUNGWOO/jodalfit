import "server-only";
import { unstable_cache } from "next/cache";
import { getServerSupabase } from "./supabase-server";
import type { NoticeInsight } from "@/types/recommendations";

const SUMMARY_COLS =
  "bid_ntce_no,bid_ntce_nm,bsns_div_nm,dmnd_instt_nm,ntce_instt_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,bidprc_psbl_indstryty_nm,prtcpt_psbl_rgn_nm,cntrct_cncls_mthd_nm,rgn_lmt_yn";

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
  insight: NoticeInsight | null;
  preSpecs: PreSpec[];
  opinions: PreSpecOpinion[];
  orderPlans: OrderPlan[];
  awards: Award[];
  contracts: Contract[];
}

const BID_NOTICE_COLUMNS =
  "bid_ntce_no,bid_ntce_ord,bid_ntce_nm,bsns_div_nm,bid_ntce_date,bid_clse_date,openg_date,presmpt_prce,asign_bdgt_amt,ntce_instt_nm,dmnd_instt_nm,bidprc_psbl_indstryty_nm,bidwinr_dcsn_mthd_nm,cntrct_cncls_mthd_nm,bid_ntce_url,rgn_lmt_yn,prtcpt_psbl_rgn_nm,indstryty_lmt_yn,attachments,embedding";

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

  // 5개 라이프사이클 단계 + 첨부문서 인사이트 병렬 조회
  const [insightRes, preSpecsRes, orderPlansRes, awardsRes, contractsRes] =
    await Promise.all([
      c
        .from("bid_notice_insights")
        .select("summary,scope,requirements,evaluation,schedule,keywords")
        .eq("bid_ntce_no", notice.bid_ntce_no)
        .eq("bid_ntce_ord", notice.bid_ntce_ord)
        .maybeSingle(),
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
    insight: (insightRes.data as NoticeInsight | null) ?? null,
    preSpecs,
    opinions,
    orderPlans: (orderPlansRes.data as OrderPlan[]) ?? [],
    awards: (awardsRes.data as Award[]) ?? [],
    contracts: (contractsRes.data as Contract[]) ?? [],
  };
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
    .select("bid_ntce_no,bid_ntce_ord,embedding")
    .eq("bid_ntce_no", bidNtceNo)
    .order("bid_ntce_ord", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!src?.embedding) return [];

  // 2) match_bid_notices RPC 호출 (오늘 이후 마감만)
  const today = new Date().toISOString().slice(0, 10);
  const candidatePool = limit * 4 + 5; // 자기 자신 제외 여유분
  const { data } = await c.rpc("match_bid_notices", {
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

/** sitemap용 — 최근 입찰공고 목록 (dedupe by bid_ntce_no) */
export async function fetchRecentNoticesForSitemap(
  limit = 5000
): Promise<{ bid_ntce_no: string; updated_at: string }[]> {
  const c = getServerSupabase();
  const seen = new Set<string>();
  const deduped: { bid_ntce_no: string; updated_at: string }[] = [];
  // PostgREST가 1000행에서 끊으므로(max_rows) range로 나눠 받는다.
  // 같은 공고가 여러 행으로 들어오므로 dedupe 후 limit을 채울 때까지 돈다.
  const PAGE = 1000;
  for (let from = 0; deduped.length < limit && from < limit * 2; from += PAGE) {
    const { data } = await c
      .from("bid_notices")
      .select("bid_ntce_no,updated_at")
      .order("bid_ntce_date", { ascending: false })
      .order("bid_ntce_no", { ascending: true })
      .range(from, from + PAGE - 1);
    if (!data?.length) break;
    for (const r of data as { bid_ntce_no: string; updated_at: string }[]) {
      if (!r.bid_ntce_no || seen.has(r.bid_ntce_no)) continue;
      seen.add(r.bid_ntce_no);
      deduped.push(r);
      if (deduped.length >= limit) break;
    }
    if (data.length < PAGE) break;
  }
  return deduped;
}

/** 인덱스 페이지용 — 진행 중 공고 (마감일 안 지남) */
export interface NoticeSummary {
  bid_ntce_no: string;
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

function applyFilters<T>(
  q: T,
  today: string,
  f: NoticeFilters
): T {
  // chainable에 cast가 어려워 any 사용 (Supabase builder)
  let qq = q as any;
  qq = qq.gte("bid_clse_date", today);
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
  return qq as T;
}

function orderClause<T>(q: T, sort: NoticeFilters["sort"]): T {
  const qq = q as any;
  switch (sort) {
    case "price_desc":
      return qq.order("presmpt_prce", { ascending: false, nullsFirst: false }) as T;
    case "close":
      return qq.order("bid_clse_date") as T;
    // 기본 신규순 — 마감 임박순이 기본이면 첫 화면이 D-1 일색이라 "늦은 공고만 있다" 인상을 줌
    case "ntce_desc":
    default:
      return qq.order("bid_ntce_date", { ascending: false, nullsFirst: false }) as T;
  }
}

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
