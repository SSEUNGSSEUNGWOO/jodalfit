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
