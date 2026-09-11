import { getServerSupabase } from "@/lib/supabase-server";

/**
 * 업종별 기업 디렉토리 — materialized view `industry_companies` / `industry_directory` (migration 0027).
 * 하루 한 번 갱신되는 고정 스냅샷이라 (indstryty_cd, seq) 창(window)만 읽는다.
 */

export const INDUSTRY_PER_PAGE = 50;

/** 이보다 업체 수가 적은 업종은 목록·사이트맵에 싣지 않는다 (얇은 페이지 방지). */
export const INDUSTRY_MIN_COMPANIES = 20;

export interface IndustryRow {
  indstryty_cd: string;
  indstryty_nm: string;
  company_count: number;
}

export interface IndustryCompanyRow {
  bizrno: string;
  bizrno_norm: string;
  corp_nm: string;
  rgn_nm: string | null;
  corp_bsns_div_nm: string | null;
}

export const isIndustryCode = (code: string) => /^[0-9A-Za-z]{1,10}$/.test(code);

/** 업체 수 많은 순 업종 목록. */
export async function fetchIndustryDirectory(
  minCompanies = INDUSTRY_MIN_COMPANIES
): Promise<IndustryRow[]> {
  const c = getServerSupabase();
  const { data, error } = await c
    .from("industry_directory")
    .select("indstryty_cd,indstryty_nm,company_count")
    .gte("company_count", minCompanies)
    .order("company_count", { ascending: false })
    .order("indstryty_cd", { ascending: true })
    .limit(1000);
  if (error) throw new Error(`industry_directory: ${error.message}`);
  return (data as IndustryRow[]) ?? [];
}

export async function fetchIndustry(code: string): Promise<IndustryRow | null> {
  const c = getServerSupabase();
  const { data } = await c
    .from("industry_directory")
    .select("indstryty_cd,indstryty_nm,company_count")
    .eq("indstryty_cd", code)
    .maybeSingle();
  return (data as IndustryRow | null) ?? null;
}

export async function fetchIndustryCompanies(
  code: string,
  page: number
): Promise<IndustryCompanyRow[]> {
  const c = getServerSupabase();
  const from = (page - 1) * INDUSTRY_PER_PAGE;
  const { data, error } = await c
    .from("industry_companies")
    .select("bizrno,bizrno_norm,corp_nm,rgn_nm,corp_bsns_div_nm")
    .eq("indstryty_cd", code)
    .gte("seq", from)
    .lt("seq", from + INDUSTRY_PER_PAGE)
    .order("seq", { ascending: true });
  if (error) throw new Error(`industry_companies ${code}: ${error.message}`);
  return (data as IndustryCompanyRow[]) ?? [];
}
