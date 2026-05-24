import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { BidCard } from "@/components/BidCard";
import { CompanyCard } from "@/components/CompanyCard";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { FilterPanel } from "@/components/FilterPanel";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { KeywordFallback } from "@/components/KeywordFallback";
import { SearchForm } from "@/components/SearchForm";
import { getRecommendations } from "@/lib/api";
import { MOCK_RESPONSE } from "@/lib/mock-data";
import type { RecommendationResponse } from "@/types/recommendations";

interface PageProps {
  searchParams: Promise<{
    company?: string;
    q?: string;
    mode?: string;
  }>;
}

export default async function RecommendationsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const isKeywords = params.mode === "keywords";
  const companyQuery = (params.company ?? "").trim();
  const keywordsQuery = (params.q ?? "").trim();

  return (
    <>
      <Header />
      <main className="flex-1">
        <Suspense fallback={<LoadingState label={isKeywords ? keywordsQuery : companyQuery} />}>
          <Results
            companyQuery={companyQuery}
            keywordsQuery={keywordsQuery}
            isKeywords={isKeywords}
            useMock={params.mode === "mock"}
          />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}

async function Results({
  companyQuery,
  keywordsQuery,
  isKeywords,
  useMock,
}: {
  companyQuery: string;
  keywordsQuery: string;
  isKeywords: boolean;
  useMock: boolean;
}) {
  // 입력 자체가 비어있으면 폴백 UI 노출
  if (isKeywords && !keywordsQuery) {
    return (
      <div className="mx-auto max-w-[720px] px-5 sm:px-8 py-16 sm:py-20">
        <KeywordFallback
          title="키워드를 입력해주세요"
          subtitle="관심 있는 공고의 영역을 자유롭게 적어주세요."
        />
      </div>
    );
  }
  if (!isKeywords && !companyQuery) {
    return <EmptyState query="" />;
  }

  let data: RecommendationResponse;
  if (useMock) {
    data = MOCK_RESPONSE;
  } else {
    data = await getRecommendations({
      query: isKeywords ? keywordsQuery : companyQuery,
      mode: isKeywords ? "keywords" : "company",
      limit: 5,
      with_explanation: true,
    });
  }

  // 키워드 모드: 회사 카드 없음, 결과만
  if (isKeywords || data.mode === "keywords") {
    return (
      <KeywordResults query={keywordsQuery} data={data} companyContext={companyQuery} />
    );
  }

  // 회사 식별 실패 또는 벡터 없음 → 키워드 폴백
  if (data.fallback === "keywords") {
    return (
      <CompanyFallback
        companyQuery={companyQuery}
        company={data.company}
        message={data.error}
      />
    );
  }

  // 회사 식별 실패 (404 케이스도 fallback 제공 안 한 경우)
  if (!data.company) {
    return <EmptyState query={companyQuery} error={data.error} />;
  }

  return <CompanyResults query={companyQuery} data={data} />;
}

function SubHeader({
  title,
  subtitle,
  searchDefault,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  searchDefault?: string;
}) {
  return (
    <section className="border-b border-border bg-muted/30">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-7 sm:py-9 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[24px] sm:text-[28px] font-extrabold tracking-tight text-foreground">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-[12.5px] text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <SearchForm
          variant="compact"
          defaultValue={searchDefault ?? ""}
          className="w-full sm:w-[280px]"
        />
      </div>
    </section>
  );
}

function CompanyResults({
  query,
  data,
}: {
  query: string;
  data: RecommendationResponse;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <>
      <SubHeader
        title={
          <>
            {query}
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              의 추천 공고
            </span>
          </>
        }
        subtitle={`과거 낙찰 이력 + 유사 공고 분석 · 매일 갱신 · ${today}`}
        searchDefault={query}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        {data.company && (
          <CompanyCard
            company={data.company}
            meta={{
              contractCount: 14,
              primarySectors: ["교육기관", "공공기관 SI", "유지보수"],
            }}
          />
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          <div>
            <div className="flex items-baseline justify-between mb-5">
              <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-foreground">
                TOP {data.results.length} 공고
              </h2>
              <span className="text-[12.5px] text-muted-foreground font-medium">
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

          <div className="lg:order-2">
            <FilterPanel />
          </div>
        </div>
      </div>
    </>
  );
}

function KeywordResults({
  query,
  data,
  companyContext,
}: {
  query: string;
  data: RecommendationResponse;
  companyContext?: string;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <>
      <SubHeader
        title={
          <>
            <span className="font-serif italic">“{query}”</span>
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              키워드로 매칭한 공고
            </span>
          </>
        }
        subtitle={`키워드 임베딩 매칭 · 매일 갱신 · ${today}`}
        searchDefault={companyContext || ""}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        <div className="grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          <div>
            {data.results.length > 0 ? (
              <>
                <div className="flex items-baseline justify-between mb-5">
                  <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-foreground">
                    TOP {data.results.length} 공고
                  </h2>
                  <span className="text-[12.5px] text-muted-foreground font-medium">
                    유사도 순
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
              </>
            ) : (
              <div className="rounded-xl bg-muted/40 border border-border p-8 text-center">
                <h3 className="text-[18px] font-bold text-foreground">
                  매칭되는 공고가 없어요.
                </h3>
                <p className="mt-2 text-[14px] text-muted-foreground">
                  키워드를 좀 더 구체적으로 입력해보세요.
                </p>
              </div>
            )}

            <div className="mt-10">
              <KeywordFallback
                title="다른 키워드로도 찾아볼까요?"
                subtitle="여러 영역을 시도해보면 더 적합한 공고를 발견할 수 있어요."
                defaultQuery={query}
              />
            </div>

            <div className="mt-12">
              <EmailCaptureForm />
            </div>
          </div>

          <div className="lg:order-2">
            <FilterPanel />
          </div>
        </div>
      </div>
    </>
  );
}

function CompanyFallback({
  companyQuery,
  company,
  message,
}: {
  companyQuery: string;
  company: RecommendationResponse["company"];
  message?: string;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <>
      <SubHeader
        title={
          <>
            {companyQuery}
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              {company ? "의 추천 공고" : ""}
            </span>
          </>
        }
        subtitle={`회사 식별 ${company ? "완료" : "실패"} · ${today}`}
        searchDefault={companyQuery}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        {company && (
          <CompanyCard
            company={company}
            meta={undefined}
            className="opacity-90"
          />
        )}

        {message && (
          <div className="mt-5 rounded-xl bg-orange-50 border border-orange-200 px-4 py-3 text-[13.5px] text-foreground">
            <span className="font-bold text-orange-700 mr-1">분석 데이터 부족:</span>
            {message}
          </div>
        )}

        <div className="mt-8">
          <KeywordFallback />
        </div>

        <div className="mt-12 max-w-[820px]">
          <EmailCaptureForm />
        </div>
      </div>
    </>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="mx-auto max-w-[640px] px-5 py-24 sm:py-28 text-center">
      <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" aria-hidden />
      <p className="mt-6 text-[15.5px] text-muted-foreground">
        <span className="font-bold text-foreground">{label || "—"}</span>에 맞는 공고를 분석하는 중...
      </p>
      <p className="mt-1.5 text-[12.5px] text-muted-foreground/70">보통 5~12초 걸려요</p>
    </div>
  );
}

function EmptyState({ query, error }: { query: string; error?: string }) {
  return (
    <div className="mx-auto max-w-[720px] px-5 py-16 sm:py-24">
      <div className="text-center mb-8">
        <h2 className="text-[26px] font-extrabold tracking-tight text-foreground">
          {query ? "회사를 찾지 못했어요." : "회사명을 입력해주세요."}
        </h2>
        <p className="mt-3 text-[14.5px] text-muted-foreground">
          {error ||
            "정확한 회사명 또는 사업자번호로 다시 검색하거나, 관심 키워드로 추천 받을 수 있어요."}
        </p>
        <div className="mt-6">
          <SearchForm defaultValue={query} />
        </div>
      </div>

      <KeywordFallback
        title="회사명이 없어도 괜찮아요"
        subtitle="관심 있는 공고 영역을 직접 입력해주시면 그 키워드로 가장 잘 맞는 공고를 찾아드릴게요."
      />
    </div>
  );
}
