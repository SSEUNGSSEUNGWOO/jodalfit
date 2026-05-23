import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { BidCard } from "@/components/BidCard";
import { CompanyCard } from "@/components/CompanyCard";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { FilterPanel } from "@/components/FilterPanel";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { getRecommendations } from "@/lib/api";
import { MOCK_RESPONSE } from "@/lib/mock-data";
import type { RecommendationResponse } from "@/types/recommendations";

interface PageProps {
  searchParams: Promise<{ company?: string; mock?: string }>;
}

export default async function RecommendationsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const query = (params.company ?? "").trim();

  return (
    <>
      <Header />
      <main className="flex-1">
        <Suspense fallback={<LoadingState query={query} />}>
          <Results query={query} useMock={params.mock === "1"} />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}

async function Results({
  query,
  useMock,
}: {
  query: string;
  useMock: boolean;
}) {
  let data: RecommendationResponse;
  if (!query) {
    data = { company: null, results: [], error: "회사명을 입력해주세요" };
  } else if (useMock) {
    data = MOCK_RESPONSE;
  } else {
    data = await getRecommendations({
      query,
      limit: 5,
      with_explanation: true,
    });
    // Fallback to mock if backend fails (dev convenience)
    if (data.error && data.results.length === 0) {
      data = { ...MOCK_RESPONSE, error: data.error };
    }
  }

  if (!data.company) {
    return <EmptyState query={query} error={data.error} />;
  }

  return (
    <>
      <SubHeader query={query} />
      <div className="mx-auto max-w-[1180px] px-6 pb-16 sm:px-8 sm:pb-20">
        <CompanyCard
          company={data.company}
          meta={{
            contractCount: 14,
            primarySectors: ["교육기관", "공공기관 SI", "유지보수"],
          }}
        />

        {data.error && (
          <div className="mt-4 rounded-tile border border-warning bg-warning-50 px-4 py-3 text-[13.5px] text-ink">
            <span className="font-semibold text-warning">참고:</span>{" "}
            {data.error}. 샘플 데이터로 표시합니다.
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          {/* Bid list */}
          <div>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="eyebrow text-teal-700">추천 결과</span>
                <h2 className="mt-1 text-[22px] font-bold tracking-tight text-ink-strong">
                  TOP {data.results.length} 공고
                </h2>
              </div>
              <span className="text-[12px] tabular text-ink-soft">
                점수 순 정렬
              </span>
            </div>

            <div className="mt-6 flex flex-col gap-5">
              {data.results.map((bid, i) => (
                <BidCard key={`${bid.bid_ntce_no}-${bid.bid_ntce_ord}`} bid={bid} rank={i + 1} />
              ))}
            </div>

            <div className="mt-12">
              <EmailCaptureForm />
            </div>
          </div>

          {/* Filter sidebar */}
          <div className="lg:order-2">
            <FilterPanel />
          </div>
        </div>
      </div>
    </>
  );
}

function SubHeader({ query }: { query: string }) {
  return (
    <section className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[1180px] flex-wrap items-end justify-between gap-4 px-6 py-7 sm:px-8 sm:py-9">
        <div>
          <span className="eyebrow text-ink-muted">검색어</span>
          <h1 className="mt-1 flex items-baseline gap-2 text-[26px] font-bold tracking-tight text-ink-strong">
            <span>{query}</span>
            <span className="text-[14px] font-normal text-ink-muted">의 추천 공고</span>
          </h1>
          <p className="mt-1 text-[12.5px] tabular text-ink-soft">
            과거 낙찰 이력 + 유사 공고 분석 · 매일 갱신 ·{" "}
            {new Date().toLocaleDateString("ko-KR")}
          </p>
        </div>
        <SearchForm variant="compact" defaultValue={query} className="w-full sm:w-[300px]" />
      </div>
    </section>
  );
}

function LoadingState({ query }: { query: string }) {
  return (
    <div className="mx-auto max-w-[1180px] px-6 py-20 text-center sm:px-8 sm:py-28">
      <Loader2 className="mx-auto h-7 w-7 animate-spin text-teal-500" aria-hidden />
      <p className="mt-5 text-[15px] text-ink-muted">
        <span className="font-semibold text-ink">{query || "—"}</span>의 과거 낙찰 이력을 분석하는 중...
      </p>
      <p className="mt-1 text-[12.5px] tabular text-ink-soft">
        보통 2~5초가 걸립니다
      </p>
    </div>
  );
}

function EmptyState({ query, error }: { query: string; error?: string }) {
  return (
    <div className="mx-auto max-w-[640px] px-6 py-20 text-center sm:py-28">
      <span className="eyebrow text-ink-muted">결과 없음</span>
      <h2 className="mt-3 text-[26px] font-bold tracking-tight text-ink-strong">
        {query
          ? "회사를 찾지 못했습니다."
          : "회사명을 입력해주세요."}
      </h2>
      <p className="mt-3 text-[14.5px] text-ink-muted">
        {error ||
          "정확한 회사명 또는 사업자번호로 다시 검색해보세요. 회사가 나라장터 등록 업체가 아닐 수 있습니다."}
      </p>
      <div className="mx-auto mt-8 max-w-[420px]">
        <SearchForm defaultValue={query} />
      </div>
    </div>
  );
}
