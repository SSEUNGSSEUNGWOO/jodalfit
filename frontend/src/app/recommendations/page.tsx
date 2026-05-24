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
    if (data.error && data.results.length === 0) {
      data = { ...MOCK_RESPONSE, error: data.error };
    }
  }

  if (!data.company) {
    return <EmptyState query={query} error={data.error} />;
  }

  const today = new Date().toLocaleDateString("ko-KR");

  return (
    <>
      {/* Sub-header */}
      <section className="border-b border-line bg-bg-soft/40">
        <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-7 sm:py-9 flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="text-[13px] font-semibold text-ink-4">검색어</span>
            <h1 className="mt-1 text-[24px] sm:text-[28px] font-extrabold tracking-tight text-ink">
              {query}
              <span className="ml-2 text-[15px] font-medium text-ink-4">의 추천 공고</span>
            </h1>
            <p className="mt-1 text-[12.5px] text-ink-5">
              과거 낙찰 이력 + 유사 공고 분석 · 매일 갱신 · {today}
            </p>
          </div>
          <SearchForm
            variant="compact"
            defaultValue={query}
            className="w-full sm:w-[280px]"
          />
        </div>
      </section>

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        <CompanyCard
          company={data.company}
          meta={{
            contractCount: 14,
            primarySectors: ["교육기관", "공공기관 SI", "유지보수"],
          }}
        />

        {data.error && (
          <div className="mt-4 rounded-xl bg-warning-soft border border-warning/30 px-4 py-3 text-[13.5px] text-ink-2">
            <span className="font-bold text-warning mr-1">참고:</span>
            {data.error}. 샘플 데이터로 표시해요.
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          {/* Bid list */}
          <div>
            <div className="flex items-baseline justify-between mb-5">
              <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-ink">
                TOP {data.results.length} 공고
              </h2>
              <span className="text-[12.5px] text-ink-5 font-medium">
                점수 순
              </span>
            </div>

            <div className="flex flex-col gap-4">
              {data.results.map((bid, i) => (
                <BidCard
                  key={`${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                  bid={bid}
                  rank={i + 1}
                />
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

function LoadingState({ query }: { query: string }) {
  return (
    <div className="mx-auto max-w-[640px] px-5 py-24 sm:py-28 text-center">
      <Loader2 className="mx-auto h-7 w-7 animate-spin text-brand" aria-hidden />
      <p className="mt-6 text-[15.5px] text-ink-3">
        <span className="font-bold text-ink">{query || "—"}</span>의 과거 낙찰 이력을 분석하는 중...
      </p>
      <p className="mt-1.5 text-[12.5px] text-ink-5">보통 5~12초 걸려요</p>
    </div>
  );
}

function EmptyState({
  query,
  error,
}: {
  query: string;
  error?: string;
}) {
  return (
    <div className="mx-auto max-w-[560px] px-5 py-24 sm:py-28 text-center">
      <h2 className="text-[26px] font-extrabold tracking-tight text-ink">
        {query ? "회사를 찾지 못했어요." : "회사명을 입력해주세요."}
      </h2>
      <p className="mt-3 text-[14.5px] text-ink-3">
        {error ||
          "정확한 회사명 또는 사업자번호로 다시 검색해보세요. 회사가 나라장터 등록 업체가 아닐 수 있어요."}
      </p>
      <div className="mt-8">
        <SearchForm defaultValue={query} />
      </div>
    </div>
  );
}
