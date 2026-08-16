import type { Metadata } from "next";
import { BoardSearch } from "@/components/board/BoardSearch";
import { BoardView } from "@/components/board/BoardView";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

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
      <main className="flex-1 flex flex-col">
        {query ? (
          <BoardView
            key={`${mode}:${query}:${hybridKeywords}:${algorithm}`}
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
      <Footer className="mt-0" />
    </>
  );
}

// 콜드스타트 보강 — 키워드 모드에서 자주 검색되는 도메인을 미리 큐레이션.
// 단일 단어보다 2~3개 복합 키워드로 의미 매칭 정확도 향상.
const CATEGORY_KEYWORDS = [
  "위탁교육 직무역량",
  "정보시스템 유지보수",
  "시설물 유지관리",
  "콘텐츠 영상 제작",
  "AI 데이터 분석",
  "급식 식자재",
  "행사 운영",
  "조경 관리",
];

function EmptyState({ mode }: { mode: Mode }) {
  return (
    <div className="world-gc flex-1">
      <div className="mx-auto max-w-[720px] px-5 py-16 sm:py-24">
        <h1 className="font-gc-serif font-black text-[26px] sm:text-[32px] tracking-[-0.02em] text-gc-ink break-keep">
          {mode === "company"
            ? "어느 회사의 판을 열까요?"
            : "어떤 공고를 찾을까요?"}
        </h1>
        <p className="mt-3 text-[14.5px] leading-[1.7] text-gc-ink-2 break-keep">
          {mode === "company"
            ? "회사명 또는 사업자번호를 입력하면 등록업종·공급물품·수주 이력을 대조해 검토 우선순위를 정리합니다."
            : "관심 영역을 입력하면 의미가 가까운 공고를 찾습니다."}
        </p>
        <div className="mt-8">
          <BoardSearch
            initialMode={mode}
            examples={{ keywords: CATEGORY_KEYWORDS }}
          />
        </div>
      </div>
    </div>
  );
}
