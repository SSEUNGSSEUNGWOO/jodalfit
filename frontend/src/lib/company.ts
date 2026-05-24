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

export async function fetchCompanyByBizrno(
  bizrnoNorm: string
): Promise<CompanyDetail | null> {
  if (!/^\d{10}$/.test(bizrnoNorm)) return null;
  const c = getServerSupabase();
  const { data } = await c
    .from("companies")
    .select(
      "bizrno,bizrno_norm,corp_nm,english_nm,ceo_nm,rgn_nm,corp_bsns_div_nm,mnfctr_div_nm,embedding,is_restricted"
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

/** 회사 마스터 페이지 SEO용 — 사업자번호로 활동 회사들 페이지네이션 */
export async function fetchActiveCompaniesForSitemap(
  limit = 5000
): Promise<{ bizrno_norm: string; updated_at: string }[]> {
  const c = getServerSupabase();
  const { data } = await c
    .from("companies")
    .select("bizrno_norm,updated_at")
    .not("bizrno_norm", "is", null)
    .limit(limit);
  return (data as { bizrno_norm: string; updated_at: string }[]) ?? [];
}
