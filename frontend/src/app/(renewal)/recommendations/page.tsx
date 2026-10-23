// frontend/src/app/(renewal)/recommendations/page.tsx
// 결과 페이지. URL 계약은 옛 페이지 그대로: company=회사명|사업자번호 / q=키워드 / keywords=하이브리드 / algorithm=v1|v2 / from=company. 공고번호면 공고 상세로.
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { PageHead } from "@/components/PageHead";
import { SearchBox } from "@/components/SearchBox";
import { ResultsView } from "@/components/results/ResultsView";
import { getSessionUser } from "@/lib/auth";
import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";
import { fetchCompanyByBizrno } from "@/lib/company";
import type { CompanyDigest } from "@/types/recommendations";

export const metadata: Metadata = { title: "추천 공고 | 조달핏", robots: { index: false, follow: false } };

const NOTICE_NO = /^\s*(R\d{2}[A-Z]{2}\d{6,})(?:-\d{3})?\s*$/i;

export default async function RecommendationsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const p = await searchParams;
  const one = (k: string) => { const v = p[k]; return (Array.isArray(v) ? v[0] : v)?.trim() || ""; };
  const company = one("company"), q = one("q"), keywords = one("keywords") || null, from = one("from") || null;
  const algorithm = one("algorithm") === "v1" ? "v1" : "v2";
  const query = company || q;
  const m = query.match(NOTICE_NO);
  if (m) redirect(`/notices/${m[1].toUpperCase()}`);

  const bizrnoNorm = company.replace(/\D/g, "");
  const [user, companyRow] = await Promise.all([
    getSessionUser(),
    bizrnoNorm.length === 10 ? fetchCompanyByBizrno(bizrnoNorm) : Promise.resolve(null),
  ]);
  const [saved, reviewed] = user ? await Promise.all([getSavedCompanyKeys(), getReviewedKeys()]) : [new Set<string>(), new Set<string>()];
  const qs = new URLSearchParams(Object.entries(p).flatMap(([k, v]) => (typeof v === "string" ? [[k, v]] : []))).toString();
  const next = `/recommendations${qs ? `?${qs}` : ""}`;
  // 사업자번호 질의 — 회사 이름을 서버에서 미리 알아 h1 에 질의 원문 대신 즉시 보여준다. 비공개 요청 회사는 null(백엔드가 키워드로 폴백).
  const initialCompany: CompanyDigest | null = companyRow && !companyRow.optout_at
    ? { bizrno: companyRow.bizrno, corp_nm: companyRow.corp_nm, rgn_nm: companyRow.rgn_nm ?? undefined }
    : null;

  if (!query) {
    return (
      <>
        <PageHead title="추천 공고" meta={["회사명 · 사업자등록번호 · 업종 또는 품목으로 검색"]} />
        <div className="mt-6"><SearchBox autoFocus /></div>
      </>
    );
  }
  return (
    <ResultsView key={`${company ? "company" : "keywords"}:${query}:${keywords ?? ""}:${algorithm}`}
      query={query} mode={company ? "company" : "keywords"} keywords={keywords} algorithm={algorithm} from={from}
      loggedIn={!!user} savedKeys={[...saved]} reviewedKeys={[...reviewed]} next={next} initialCompany={initialCompany} />
  );
}
