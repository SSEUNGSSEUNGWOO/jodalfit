import "server-only";
import { getServerSupabase } from "./supabase-server";

export interface CompanyDetail {
  bizrno: string;
  bizrno_norm: string;
  corp_nm: string;
  english_nm: string | null;
  ceo_nm: string | null;
  rgn_nm: string | null;
  corp_bsns_div_nm: string | null;
  mnfctr_div_nm: string | null;
  has_embedding: boolean;
  is_restricted: boolean;
  contract_count: number;
}

export interface ContractRow {
  cntrct_no: string;
  cntrct_nm: string | null;
  bsns_div_nm: string | null;
  cntrct_amt: number | null;
  cntrct_cncls_date: string | null;
  dmnd_instt_nm: string | null;
}

export interface AwardRow {
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_amt: number | null;
  bid_rate: number | null;
  bsns_div_nm: string | null;
  bid_ntce_nm: string | null;
  dmnd_instt_nm: string | null;
  bid_clse_date: string | null;
}

export interface AwardSummary {
  count: number;
  avg_rate: number | null;
  min_rate: number | null;
  max_rate: number | null;
  total_amt: number;
}

export interface PeerRateStat {
  /** 표본 평균 투찰율 (%) */
  avg: number;
  /** 표본 크기 */
  n: number;
}

/** 발주기관별 과거 낙찰 평균 투찰율 batch 조회.
 *  추천 카드에 "이 기관 비슷한 공고 평균 XX% (n건)" 인사이트용. */
export async function fetchPeerRateByInstitution(
  institutionNames: string[]
): Promise<Map<string, PeerRateStat>> {
  const out = new Map<string, PeerRateStat>();
  const names = Array.from(new Set(institutionNames.filter(Boolean)));
  if (names.length === 0) return out;
  const c = getServerSupabase();
  // award_results에서 직접 dmnd_instt_nm로 join — bid_notices와 매번 join 비용 회피
  // award_results에는 dmnd_instt_nm 없으니 bid_notices에서 (bid_ntce_no) 모은 후 rate fetch.
  // → 두 단계: 기관별 bid_ntce_no 모음 → rate 모음.
  const { data: noticeRows } = await c
    .from("bid_notices")
    .select("bid_ntce_no,bid_ntce_ord,dmnd_instt_nm")
    .in("dmnd_instt_nm", names)
    .limit(5000);
  type NoticeRow = { bid_ntce_no: string; bid_ntce_ord: string; dmnd_instt_nm: string | null };
  const noticeToInstt = new Map<string, string>();
  for (const r of (noticeRows as NoticeRow[]) ?? []) {
    if (r.dmnd_instt_nm) noticeToInstt.set(`${r.bid_ntce_no}|${r.bid_ntce_ord}`, r.dmnd_instt_nm);
  }
  if (noticeToInstt.size === 0) return out;

  const bidNos = Array.from(new Set([...noticeToInstt.keys()].map((k) => k.split("|")[0])));
  type RateRow = { bid_ntce_no: string; bid_ntce_ord: string; bid_rate: number | null };
  const ratesByInstt: Record<string, number[]> = {};
  // bid_nos가 많을 수 있어 페이지 단위로
  const PAGE = 500;
  for (let i = 0; i < bidNos.length; i += PAGE) {
    const sub = bidNos.slice(i, i + PAGE);
    const { data: rateRows } = await c
      .from("award_results")
      .select("bid_ntce_no,bid_ntce_ord,bid_rate")
      .in("bid_ntce_no", sub)
      .eq("is_winner", true)
      .not("bid_rate", "is", null);
    for (const r of (rateRows as RateRow[]) ?? []) {
      const instt = noticeToInstt.get(`${r.bid_ntce_no}|${r.bid_ntce_ord}`);
      if (!instt || r.bid_rate == null) continue;
      (ratesByInstt[instt] ??= []).push(r.bid_rate);
    }
  }
  for (const [instt, rates] of Object.entries(ratesByInstt)) {
    if (rates.length === 0) continue;
    out.set(instt, {
      avg: rates.reduce((s, v) => s + v, 0) / rates.length,
      n: rates.length,
    });
  }
  return out;
}

export interface CompanySectors {
  bsns_div_counts: Record<string, number>;
  top_institutions: string[];
}

export interface CompanyProfile {
  industries: string[]; // 등록업종 (대표 먼저)
  products: string[]; // 공급물품 (대표 먼저)
}

export async function fetchCompanyProfile(bizrno: string): Promise<CompanyProfile> {
  const c = getServerSupabase();
  const [indRes, prdRes] = await Promise.all([
    c
      .from("company_industries")
      .select("indstryty_nm,rprsnt_indstryty_yn")
      .eq("bizrno", bizrno),
    c
      .from("company_supply_products")
      .select("dtl_prdct_clsfc_nm,rprsnt_prdct_yn")
      .eq("bizrno", bizrno),
  ]);
  const industries: string[] = [];
  for (const r of (indRes.data as { indstryty_nm: string | null; rprsnt_indstryty_yn: string | null }[]) ?? []) {
    if (!r.indstryty_nm) continue;
    if (r.rprsnt_indstryty_yn === "Y") industries.unshift(r.indstryty_nm);
    else industries.push(r.indstryty_nm);
  }
  const products: string[] = [];
  for (const r of (prdRes.data as { dtl_prdct_clsfc_nm: string | null; rprsnt_prdct_yn: string | null }[]) ?? []) {
    if (!r.dtl_prdct_clsfc_nm) continue;
    if (r.rprsnt_prdct_yn === "Y") products.unshift(r.dtl_prdct_clsfc_nm);
    else products.push(r.dtl_prdct_clsfc_nm);
  }
  return { industries, products };
}

export async function fetchCompanyByBizrno(
  bizrnoNorm: string
): Promise<CompanyDetail | null> {
  if (!/^\d{10}$/.test(bizrnoNorm)) return null;
  const c = getServerSupabase();
  const { data } = await c
    .from("companies")
    .select(
      "bizrno,bizrno_norm,corp_nm,english_nm,ceo_nm,rgn_nm,corp_bsns_div_nm,mnfctr_div_nm,embedding,is_restricted,contract_count"
    )
    .eq("bizrno_norm", bizrnoNorm)
    .limit(1)
    .maybeSingle();

  if (!data) return null;
  return {
    bizrno: data.bizrno,
    bizrno_norm: data.bizrno_norm,
    corp_nm: data.corp_nm,
    english_nm: data.english_nm,
    ceo_nm: data.ceo_nm,
    rgn_nm: data.rgn_nm,
    corp_bsns_div_nm: data.corp_bsns_div_nm,
    mnfctr_div_nm: data.mnfctr_div_nm,
    has_embedding: !!data.embedding,
    is_restricted: !!data.is_restricted,
    contract_count: data.contract_count ?? 0,
  };
}

export async function fetchCompanyContracts(
  bizrnoNorm: string,
  limit = 20
): Promise<ContractRow[]> {
  const c = getServerSupabase();
  const { data } = await c
    .from("contracts")
    .select("cntrct_no,cntrct_nm,bsns_div_nm,cntrct_amt,cntrct_cncls_date,dmnd_instt_nm")
    .eq("rprsnt_corp_bizrno_norm", bizrnoNorm)
    .order("cntrct_cncls_date", { ascending: false })
    .limit(limit);
  return (data as ContractRow[]) ?? [];
}

/** 회사의 낙찰 이력 — bid_rate(투찰율) 회고용.
 *  award_results와 bid_notices 사이 FK가 없어 2번 쿼리 후 JS에서 매칭. */
export async function fetchCompanyAwards(
  bizrnoNorm: string,
  limit = 50
): Promise<AwardRow[]> {
  const c = getServerSupabase();
  const { data: awardData } = await c
    .from("award_results")
    .select("bid_ntce_no,bid_ntce_ord,bid_amt,bid_rate,bsns_div_nm")
    .eq("bizrno", bizrnoNorm)
    .eq("is_winner", true)
    .order("bid_ntce_no", { ascending: false })
    .limit(limit);
  type AwardOnly = {
    bid_ntce_no: string;
    bid_ntce_ord: string;
    bid_amt: number | null;
    bid_rate: number | null;
    bsns_div_nm: string | null;
  };
  const awards = (awardData as AwardOnly[]) ?? [];
  if (awards.length === 0) return [];

  const bidNos = Array.from(new Set(awards.map((a) => a.bid_ntce_no)));
  const { data: noticeData } = await c
    .from("bid_notices")
    .select("bid_ntce_no,bid_ntce_ord,bid_ntce_nm,dmnd_instt_nm,bid_clse_date")
    .in("bid_ntce_no", bidNos);
  type NoticeMeta = {
    bid_ntce_no: string;
    bid_ntce_ord: string;
    bid_ntce_nm: string | null;
    dmnd_instt_nm: string | null;
    bid_clse_date: string | null;
  };
  const noticeMap = new Map<string, NoticeMeta>();
  for (const n of (noticeData as NoticeMeta[]) ?? []) {
    noticeMap.set(`${n.bid_ntce_no}|${n.bid_ntce_ord}`, n);
  }

  return awards.map((a) => {
    const n = noticeMap.get(`${a.bid_ntce_no}|${a.bid_ntce_ord}`);
    return {
      bid_ntce_no: a.bid_ntce_no,
      bid_ntce_ord: a.bid_ntce_ord,
      bid_amt: a.bid_amt,
      bid_rate: a.bid_rate,
      bsns_div_nm: a.bsns_div_nm,
      bid_ntce_nm: n?.bid_ntce_nm ?? null,
      dmnd_instt_nm: n?.dmnd_instt_nm ?? null,
      bid_clse_date: n?.bid_clse_date ?? null,
    };
  });
}

export function summarizeAwards(rows: AwardRow[]): AwardSummary {
  const rates = rows
    .map((r) => r.bid_rate)
    .filter((v): v is number => v !== null && v > 0);
  const amts = rows
    .map((r) => r.bid_amt)
    .filter((v): v is number => v !== null && v > 0);
  return {
    count: rows.length,
    avg_rate: rates.length > 0 ? rates.reduce((s, v) => s + v, 0) / rates.length : null,
    min_rate: rates.length > 0 ? Math.min(...rates) : null,
    max_rate: rates.length > 0 ? Math.max(...rates) : null,
    total_amt: amts.reduce((s, v) => s + v, 0),
  };
}

export function summarizeContracts(
  rows: ContractRow[]
): CompanySectors {
  const bsns_counts: Record<string, number> = {};
  const instt_counts: Record<string, number> = {};
  for (const r of rows) {
    const k = r.bsns_div_nm || "기타";
    bsns_counts[k] = (bsns_counts[k] || 0) + 1;
    if (r.dmnd_instt_nm) {
      instt_counts[r.dmnd_instt_nm] = (instt_counts[r.dmnd_instt_nm] || 0) + 1;
    }
  }
  const top_institutions = Object.entries(instt_counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([k]) => k);
  return {
    bsns_div_counts: bsns_counts,
    top_institutions,
  };
}

/** 회사 마스터 페이지 SEO용 — 추천/이력 있는 회사만 포함 (깡통 페이지 sitemap 배제) */
export async function fetchActiveCompaniesForSitemap(
  limit = 5000
): Promise<{ bizrno_norm: string; updated_at: string }[]> {
  const c = getServerSupabase();
  const { data } = await c
    .from("companies")
    .select("bizrno_norm,updated_at,embedded_at,contract_count")
    .not("bizrno_norm", "is", null)
    .or("embedded_at.not.is.null,contract_count.gt.0")
    .order("embedded_at", { ascending: false, nullsFirst: false })
    .limit(limit);
  return (data as { bizrno_norm: string; updated_at: string }[]) ?? [];
}

/** 인덱스 페이지용 — 회사 벡터 있는 회사 우선 (추천 가능한 회사) */
export interface CompanySummary {
  bizrno: string;
  bizrno_norm: string;
  corp_nm: string;
  ceo_nm: string | null;
  rgn_nm: string | null;
  corp_bsns_div_nm: string | null;
  mnfctr_div_nm: string | null;
  hmpg_addr: string | null;
  opng_dt: string | null;
  contract_count: number | null;
  /** runtime-attached */
  recent_amount?: number;
  recent_sectors?: string[];
}

export async function fetchBrowseCompanies(
  limit = 30
): Promise<CompanySummary[]> {
  const c = getServerSupabase();
  const { data } = await c
    .from("companies")
    .select(
      "bizrno,bizrno_norm,corp_nm,ceo_nm,rgn_nm,corp_bsns_div_nm,mnfctr_div_nm,hmpg_addr,opng_dt,contract_count"
    )
    .not("embedded_at", "is", null)
    .order("embedded_at", { ascending: false })
    .limit(limit);
  const companies = (data as CompanySummary[]) ?? [];
  if (companies.length === 0) return companies;

  // 모든 회사의 contracts 한 번에 join (효율적)
  const bizrnos = companies.map((x) => x.bizrno_norm).filter(Boolean);
  const { data: contracts } = await c
    .from("contracts")
    .select("rprsnt_corp_bizrno_norm,cntrct_amt,bsns_div_nm")
    .in("rprsnt_corp_bizrno_norm", bizrnos);

  const byBiz: Record<string, { amt: number; sectors: Set<string>; cnt: number }> =
    {};
  for (const r of (contracts as any[]) ?? []) {
    const k = r.rprsnt_corp_bizrno_norm;
    if (!k) continue;
    if (!byBiz[k]) byBiz[k] = { amt: 0, sectors: new Set(), cnt: 0 };
    byBiz[k].amt += r.cntrct_amt ?? 0;
    byBiz[k].cnt += 1;
    if (r.bsns_div_nm) byBiz[k].sectors.add(r.bsns_div_nm);
  }

  return companies.map((x) => {
    const s = byBiz[x.bizrno_norm];
    return {
      ...x,
      contract_count: s?.cnt ?? x.contract_count ?? 0,
      recent_amount: s?.amt ?? 0,
      recent_sectors: s ? Array.from(s.sectors).slice(0, 3) : [],
    };
  });
}
