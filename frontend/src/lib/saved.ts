// frontend/src/lib/saved.ts
// 검토함·Nav 가 읽는 사용자 데이터. 사용자 행은 세션 클라이언트(RLS), 공개 데이터 조인은 service_role.
// 비로그인(세션 없음)이면 사용자 테이블 select 가 권한 오류 → 전부 빈 값으로 돌려준다.
import "server-only";
import { cache } from "react";
import { getServerSupabase as getSessionSupabase } from "@/lib/supabase/server";
import { getServerSupabase as getPublicSupabase } from "@/lib/supabase-server";
import { SUMMARY_COLS, type NoticeSummary } from "@/lib/notice";
import { dLeft } from "@/lib/format";
import { companyStats, type CompanyStats, type DLeft } from "@/lib/saved-stats";

type SavedCompanyKey = { bizrno_norm: string; created_at: string };
type ReviewedKey = { bid_ntce_no: string; bid_ntce_ord: string; via_bizrno_norm: string | null; why: string | null; created_at: string };

const savedCompanyRows = cache(async (): Promise<SavedCompanyKey[]> => {
  const sb = await getSessionSupabase();
  const { data, error } = await sb.from("saved_companies").select("bizrno_norm,created_at").order("created_at", { ascending: false });
  return error ? [] : ((data ?? []) as SavedCompanyKey[]);
});

const reviewedRows = cache(async (): Promise<ReviewedKey[]> => {
  const sb = await getSessionSupabase();
  const { data, error } = await sb
    .from("reviewed_notices")
    .select("bid_ntce_no,bid_ntce_ord,via_bizrno_norm,why,created_at")
    .order("created_at", { ascending: false });
  return error ? [] : ((data ?? []) as ReviewedKey[]);
});

/** StarCompany 초기값용 — 현재 사용자가 저장한 bizrno_norm 집합 */
export async function getSavedCompanyKeys(): Promise<Set<string>> {
  return new Set((await savedCompanyRows()).map((r) => r.bizrno_norm));
}

/** ReviewButton 초기값용 — `${bid_ntce_no}-${bid_ntce_ord}` 집합 */
export async function getReviewedKeys(): Promise<Set<string>> {
  return new Set((await reviewedRows()).map((r) => `${r.bid_ntce_no}-${r.bid_ntce_ord}`));
}

type CompanyLite = { bizrno: string; bizrno_norm: string; corp_nm: string; rgn_nm: string | null };

async function companiesByNorm(norms: string[]): Promise<Map<string, CompanyLite>> {
  if (norms.length === 0) return new Map();
  const { data } = await getPublicSupabase().from("companies").select("bizrno,bizrno_norm,corp_nm,rgn_nm").in("bizrno_norm", norms);
  return new Map(((data ?? []) as CompanyLite[]).map((c) => [c.bizrno_norm, c]));
}

/** Nav 메뉴용 — ★ 목록(이름)과 검토 건수 */
export async function getNavSaved(): Promise<{ savedCompanies: { bizrnoNorm: string; name: string }[]; reviewedCount: number }> {
  const [saved, reviewed] = await Promise.all([savedCompanyRows(), reviewedRows()]);
  const cos = await companiesByNorm(saved.map((r) => r.bizrno_norm));
  return {
    savedCompanies: saved.map((r) => ({ bizrnoNorm: r.bizrno_norm, name: cos.get(r.bizrno_norm)?.corp_nm ?? r.bizrno_norm })),
    reviewedCount: reviewed.length,
  };
}

export type SavedCompanyRow = {
  bizrnoNorm: string;
  name: string;
  region: string | null; // rgn_nm 원문 — 표시는 rgnBase
  industries: number;
  stats: CompanyStats | null; // 추천 캐시 없으면 null
};

/** 검토함 "저장한 회사" 탭. 숫자는 company_recommendations 캐시(마감 지난 항목 제외)에서. */
export async function getSavedCompanies(today: Date = new Date()): Promise<SavedCompanyRow[]> {
  const saved = await savedCompanyRows();
  if (saved.length === 0) return [];
  const norms = saved.map((r) => r.bizrno_norm);
  const pub = getPublicSupabase();
  const [cos, ind, reco] = await Promise.all([
    companiesByNorm(norms),
    pub.from("company_industries").select("bizrno").in("bizrno", norms), // companies.bizrno 는 10자리 그대로라 norm 과 같다
    pub.from("company_recommendations").select("bizrno_norm,payload").in("bizrno_norm", norms),
  ]);
  const indCount = new Map<string, number>();
  for (const r of (ind.data ?? []) as { bizrno: string }[]) indCount.set(r.bizrno, (indCount.get(r.bizrno) ?? 0) + 1);
  const stats = new Map<string, CompanyStats>();
  for (const r of (reco.data ?? []) as { bizrno_norm: string; payload: { results?: { bid_clse_date?: string | null }[] } }[]) {
    stats.set(r.bizrno_norm, companyStats((r.payload?.results ?? []).map((x) => x.bid_clse_date), today));
  }
  return saved.map((r) => {
    const c = cos.get(r.bizrno_norm);
    return {
      bizrnoNorm: r.bizrno_norm,
      name: c?.corp_nm ?? r.bizrno_norm,
      region: c?.rgn_nm ?? null,
      industries: indCount.get(c?.bizrno ?? r.bizrno_norm) ?? 0,
      stats: stats.get(r.bizrno_norm) ?? null,
    };
  });
}

export type ReviewedNoticeRow = {
  no: string;
  ord: string;
  title: string;
  org: string;
  via: { bizrnoNorm: string; name: string } | null;
  why: string | null;
  clse: string | null;
  price: number | null;
  d: DLeft | null; // null = 마감 날짜 없음
};

/** 검토함 "공고" 탭. 진행 중(마감 오름차순)과 마감 지남(최근 순)을 나눠 준다. */
export async function getReviewedNotices(today: Date = new Date()): Promise<{ live: ReviewedNoticeRow[]; past: ReviewedNoticeRow[] }> {
  const reviewed = await reviewedRows();
  if (reviewed.length === 0) return { live: [], past: [] };
  const pub = getPublicSupabase();
  const [nt, cos] = await Promise.all([
    pub.from("bid_notices").select(SUMMARY_COLS).in("bid_ntce_no", [...new Set(reviewed.map((r) => r.bid_ntce_no))]),
    companiesByNorm([...new Set(reviewed.map((r) => r.via_bizrno_norm).filter((x): x is string => !!x))]),
  ]);
  const byKey = new Map(((nt.data ?? []) as NoticeSummary[]).map((n) => [`${n.bid_ntce_no}-${n.bid_ntce_ord}`, n]));
  const rows: ReviewedNoticeRow[] = [];
  for (const r of reviewed) {
    const n = byKey.get(`${r.bid_ntce_no}-${r.bid_ntce_ord}`);
    if (!n) continue; // 공고가 DB 에서 사라졌으면 표시하지 않는다(정리 잡이 지운다)
    const via = r.via_bizrno_norm ? cos.get(r.via_bizrno_norm) : undefined;
    rows.push({
      no: n.bid_ntce_no,
      ord: n.bid_ntce_ord,
      title: n.bid_ntce_nm,
      org: n.dmnd_instt_nm || n.ntce_instt_nm || "—",
      via: r.via_bizrno_norm ? { bizrnoNorm: r.via_bizrno_norm, name: via?.corp_nm ?? r.via_bizrno_norm } : null,
      why: r.why,
      clse: n.bid_clse_date ?? null,
      price: n.presmpt_prce ?? n.asign_bdgt_amt ?? null,
      d: dLeft(n.bid_clse_date, today),
    });
  }
  const live = rows.filter((x) => !x.d || x.d.days >= 0).sort((a, b) => (a.clse ?? "9999").localeCompare(b.clse ?? "9999"));
  const past = rows.filter((x) => x.d && x.d.days < 0).sort((a, b) => (b.clse ?? "").localeCompare(a.clse ?? ""));
  return { live, past };
}
