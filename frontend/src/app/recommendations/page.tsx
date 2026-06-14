import type { Metadata } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { RecommendationsView } from "@/components/RecommendationsView";
import { SearchForm } from "@/components/SearchForm";

export const metadata: Metadata = {
  // 개인화된 검색 결과 페이지 — 검색엔진 인덱스 X, 봇 크롤 차단 효과도 겸함
  robots: { index: false, follow: false },
};

type Mode = "company" | "keywords";

interface PageProps {
  searchParams: Promise<{
    company?: string;
    q?: string;
    mode?: string;
  }>;
}

export default async function RecommendationsPage({ searchParams }: PageProps) {
  const p = await searchParams;
  const companyQuery = (p.company ?? "").trim();
  const keywordsQuery = (p.q ?? "").trim();
  const mode: Mode = companyQuery ? "company" : "keywords";
  const query = companyQuery || keywordsQuery;
  const useMock = p.mode === "mock";

  return (
    <>
      <Header />
      <main className="flex-1">
        {query ? (
          <RecommendationsView query={query} mode={mode} useMock={useMock} />
        ) : (
          <EmptyState mode={mode} />
        )}
      </main>
      <Footer />
    </>
  );
}

function EmptyState({ mode }: { mode: Mode }) {
  return (
    <div className="mx-auto max-w-[720px] px-5 py-16 sm:py-24">
      <div className="text-center mb-8">
        <h2 className="text-[26px] font-extrabold tracking-tight text-foreground">
          {mode === "company" ? "회사명을 입력해주세요." : "키워드를 입력해주세요."}
        </h2>
        <p className="mt-3 text-[14.5px] text-muted-foreground break-keep">
          {mode === "company"
            ? "회사명 또는 사업자번호를 입력하면 회사 기준으로 검토할 만한 공고를 추천합니다."
            : "관심 영역을 입력하면 의미가 가까운 공고를 찾습니다."}
        </p>
        <div className="mt-6">
          <SearchForm initialMode={mode} />
        </div>
      </div>
    </div>
  );
}
