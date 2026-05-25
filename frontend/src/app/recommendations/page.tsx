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
import { SlimBidRow } from "@/components/SlimBidRow";
import { getRecommendations } from "@/lib/api";
import { MOCK_RESPONSE } from "@/lib/mock-data";
import type { RecommendationResponse } from "@/types/recommendations";

const TOP_N = 5;

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

  return (
    <>
      <Header />
      <main className="flex-1">
        <Suspense fallback={<LoadingState label={query} mode={mode} />}>
          <Results
            mode={mode}
            query={query}
            useMock={p.mode === "mock"}
          />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}

async function Results({
  mode,
  query,
  useMock,
}: {
  mode: Mode;
  query: string;
  useMock: boolean;
}) {
  if (!query) {
    return <EmptyState mode={mode} />;
  }

  let data: RecommendationResponse;
  if (useMock) {
    data = MOCK_RESPONSE;
  } else {
    data = await getRecommendations({
      query,
      mode,
      limit: 20,
      with_explanation: true,
    });
  }

  if (mode === "company") {
    // 회사 식별 실패 또는 벡터 없음 → 키워드 폴백 안내
    if (data.fallback === "keywords" || !data.company) {
      return (
        <CompanyFallback
          query={query}
          company={data.company}
          message={data.error || undefined}
        />
      );
    }
    return <CompanyResults query={query} data={data} />;
  }
  return <KeywordResults query={query} data={data} />;
}

function SubHeader({
  title,
  subtitle,
  searchDefault,
  mode,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  searchDefault?: string;
  mode: Mode;
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
          initialMode={mode}
          className="w-full sm:w-[280px]"
        />
      </div>
    </section>
  );
}

function ResultsList({
  results,
  noResultText,
  semanticHintQuery,
}: {
  results: RecommendationResponse["results"];
  noResultText: string;
  semanticHintQuery?: string;
}) {
  if (results.length === 0) {
    return (
      <div className="rounded-xl bg-muted/40 border border-border p-8 text-center">
        <h3 className="text-[18px] font-bold text-foreground">{noResultText}</h3>
      </div>
    );
  }
  const top = results.slice(0, TOP_N);
  const slim = results.slice(TOP_N);
  return (
    <>
      <div className="flex flex-col gap-4">
        {top.map((bid, i) => (
          <BidCard
            key={`${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
            bid={bid}
            rank={i + 1}
            semanticHintQuery={semanticHintQuery}
          />
        ))}
      </div>
      {slim.length > 0 && (
        <section className="mt-10">
          <div className="flex items-baseline justify-between mb-3 px-3">
            <h3 className="text-[15px] font-bold text-foreground">
              관련 공고 {slim.length}개 더
            </h3>
            <span className="text-[11.5px] text-muted-foreground font-medium">
              점수 / 마감 / 예산
            </span>
          </div>
          <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
            {slim.map((bid, i) => (
              <SlimBidRow
                key={`slim-${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                bid={bid}
                rank={TOP_N + i + 1}
              />
            ))}
          </div>
        </section>
      )}
    </>
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
        mode="company"
        title={
          <>
            {query}
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              의 검토 우선순위
            </span>
          </>
        }
        subtitle={`등록업종·공급물품·수주 이력 기준 정리 · 매일 갱신 · ${today}`}
        searchDefault={query}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        {data.company && <CompanyCard company={data.company} meta={undefined} />}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          <div>
            <div className="flex items-baseline justify-between mb-5">
              <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-foreground">
                검토 우선순위 {data.results.length}건
              </h2>
              <span className="text-[12.5px] text-muted-foreground font-medium">점수 순</span>
            </div>
            <p className="mb-5 text-[12.5px] text-muted-foreground break-keep">
              매칭 점수는 검토 우선순위입니다. 낙찰 가능성이나 최종 입찰 가능 여부를 의미하지 않습니다.
            </p>
            <ResultsList
              results={data.results}
              noResultText="조건에 맞는 공고를 찾지 못했습니다. 키워드를 넓히거나 다른 모드로 시도해보세요."
            />
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
}: {
  query: string;
  data: RecommendationResponse;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <>
      <SubHeader
        mode="keywords"
        title={
          <>
            <span className="font-serif italic">“{query}”</span>
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              에 의미가 가까운 공고
            </span>
          </>
        }
        subtitle={`AI 임베딩(1536차원)으로 의미 유사도 매칭 · 같은 단어가 없어도 비슷한 의미의 공고를 찾아드려요 · 매일 갱신 · ${today}`}
        searchDefault={query}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        <div className="grid gap-8 lg:grid-cols-[1fr_240px] lg:gap-10">
          <div>
            <div className="flex items-baseline justify-between mb-5">
              <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-foreground">
                의미 매칭 공고 {data.results.length}건
              </h2>
              <span className="text-[12.5px] text-muted-foreground font-medium">
                유사도 순
              </span>
            </div>
            <ResultsList
              results={data.results}
              noResultText="조건에 맞는 공고를 찾지 못했습니다. 키워드를 더 구체적으로 입력하거나 다른 영역으로 시도해보세요."
              semanticHintQuery={query}
            />

            <div className="mt-10">
              <KeywordFallback
                title="다른 키워드로도 찾아볼까요?"
                subtitle="여러 영역을 시도하면 더 적합한 공고를 발견할 수 있어요."
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
  query,
  company,
  message,
}: {
  query: string;
  company: RecommendationResponse["company"];
  message?: string;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <>
      <SubHeader
        mode="company"
        title={
          <>
            {query}
            <span className="ml-2 text-[15px] font-medium text-muted-foreground">
              {company ? "의 추천 공고" : ""}
            </span>
          </>
        }
        subtitle={`회사 식별 ${company ? "완료" : "실패"} · ${today}`}
        searchDefault={query}
      />

      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        {company && (
          <CompanyCard company={company} meta={undefined} className="opacity-90" />
        )}
        {message && (
          <div className="mt-5 rounded-xl bg-orange-50 border border-orange-200 px-4 py-3 text-[13.5px] text-foreground break-keep">
            <span className="font-bold text-orange-700 mr-1">회사 데이터 부족:</span>
            회사 데이터가 부족해 추천 정확도가 낮을 수 있습니다. 키워드 검색으로 관심 영역을 직접 탐색할 수 있습니다.
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

function LoadingState({ label, mode }: { label: string; mode: Mode }) {
  return (
    <div className="mx-auto max-w-[640px] px-5 py-24 sm:py-28 text-center">
      <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" aria-hidden />
      <p className="mt-6 text-[15.5px] text-muted-foreground">
        나라장터 공고와 {mode === "company" ? "회사 정보" : "검색 키워드"}를 대조하고 있습니다.
        {label && (
          <>
            <br />
            <span className="font-bold text-foreground">{label}</span>
          </>
        )}
      </p>
      <p className="mt-1.5 text-[12.5px] text-muted-foreground/70">보통 5~12초 소요됩니다.</p>
    </div>
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
