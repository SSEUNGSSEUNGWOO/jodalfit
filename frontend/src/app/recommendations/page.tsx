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
    keywords?: string;
    mode?: string;
    algorithm?: string;
  }>;
}

export default async function RecommendationsPage({ searchParams }: PageProps) {
  const p = await searchParams;
  const companyQuery = (p.company ?? "").trim();
  const keywordsQuery = (p.q ?? "").trim();
  const hybridKeywords = (p.keywords ?? "").trim();
  const mode: Mode = companyQuery ? "company" : "keywords";
  const query = companyQuery || keywordsQuery;
  const useMock = p.mode === "mock";
  const algorithm = p.algorithm === "v1" ? "v1" : "v2";

  return (
    <>
      <Header />
      <main className="flex-1">
        {query ? (
          <RecommendationsView
            query={query}
            mode={mode}
            useMock={useMock}
            keywords={mode === "company" ? hybridKeywords || undefined : undefined}
            algorithm={algorithm}
          />
        ) : (
          <EmptyState mode={mode} />
        )}
      </main>
      <Footer />
    </>
  );
}

// 콜드스타트 보강 — 키워드 모드에서 자주 검색되는 도메인을 미리 큐레이션.
// 단일 단어보다 2~3개 복합 키워드로 의미 매칭 정확도 향상.
const CATEGORY_KEYWORDS = [
  "위탁교육 직무역량",
  "정보시스템 유지보수",
  "콘텐츠 영상 제작",
  "AI 데이터 분석",
  "컨설팅 진단",
  "디자인 브랜딩",
  "행사 운영",
  "클라우드 전환",
];

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
          <SearchForm
            initialMode={mode}
            examples={{ keywords: CATEGORY_KEYWORDS }}
          />
        </div>
      </div>
    </div>
  );
}
