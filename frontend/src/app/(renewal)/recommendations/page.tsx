// frontend/src/app/(renewal)/recommendations/page.tsx
// 결과 페이지. URL 계약은 옛 페이지 그대로: company=회사명|사업자번호 / q=키워드 / keywords=하이브리드 / algorithm=v1|v2 / from=company. 공고번호면 공고 상세로.
// 키워드 모드 좁히기(2026-10-28): div=물품|용역|공사 / due=7|30 — 칩이 주소를 바꾸고 페이지가 다시 마운트해 다시 계산한다(공유·뒤로가기가 그대로 된다).
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ResultsView } from "@/components/results/ResultsView";
import { getSessionUser } from "@/lib/auth";
import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";
import { fetchCompanyByBizrno } from "@/lib/company";
import type { CompanyDigest, KeywordFilter } from "@/types/recommendations";

export const metadata: Metadata = { title: "추천 공고 | 조달핏", robots: { index: false, follow: false } };

const NOTICE_NO = /^\s*(R\d{2}[A-Z]{2}\d{6,})(?:-\d{3})?\s*$/i;

export default async function RecommendationsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const p = await searchParams;
  const one = (k: string) => { const v = p[k]; return (Array.isArray(v) ? v[0] : v)?.trim() || ""; };
  const company = one("company"), q = one("q"), keywords = one("keywords") || null, from = one("from") || null;
  const algorithm = one("algorithm") === "v1" ? "v1" : "v2";
  const dv = one("div"), du = one("due");
  const filter: KeywordFilter = { div: dv === "물품" || dv === "용역" || dv === "공사" ? dv : null, due: du === "7" ? 7 : du === "30" ? 30 : null };
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

  // 입구는 루트 하나다 — 실사용자 검색의 97.7% 가 / 에서 시작한다(2026-10-23 실측).
  // 질의 없이 여기로 오면 입구로 보낸다. 입구를 두 벌 두면 갈라진다.
  if (!query) redirect("/");

  return (
    <ResultsView key={`${company ? "company" : "keywords"}:${query}:${keywords ?? ""}:${algorithm}:${filter.div ?? ""}:${filter.due ?? ""}`}
      query={query} mode={company ? "company" : "keywords"} keywords={keywords} algorithm={algorithm} from={from} filter={filter}
      loggedIn={!!user} savedKeys={[...saved]} reviewedKeys={[...reviewed]} next={next} initialCompany={initialCompany} />
  );
}
