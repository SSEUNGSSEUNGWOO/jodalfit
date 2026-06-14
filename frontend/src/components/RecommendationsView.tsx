"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { CompanyCard } from "@/components/CompanyCard";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { FilterPanel } from "@/components/FilterPanel";
import { KeywordFallback } from "@/components/KeywordFallback";
import { SearchForm } from "@/components/SearchForm";
import { SlimOrderPlanRow } from "@/components/SlimOrderPlanRow";
import { SlimPreSpecRow } from "@/components/SlimPreSpecRow";
import { StreamingResultsList } from "@/components/StreamingResultsList";
import { MOCK_RESPONSE } from "@/lib/mock-data";
import type {
  OrderPlanRecommendation,
  PreSpecRecommendation,
  RecommendationResponse,
} from "@/types/recommendations";

const TOP_N = 5;
const STAGE_LIMIT = 5;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type Mode = "company" | "keywords";

interface Props {
  query: string;
  mode: Mode;
  useMock: boolean;
  /** 회사 모드에서만 의미 — 회사 벡터 × 키워드 임베딩 0.6/0.4 하이브리드 블렌딩 */
  keywords?: string;
}

export function RecommendationsView({ query, mode, useMock, keywords }: Props) {
  const [data, setData] = useState<RecommendationResponse | null>(
    useMock ? MOCK_RESPONSE : null
  );
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [streamDone, setStreamDone] = useState<boolean>(useMock);

  useEffect(() => {
    if (useMock) {
      setData(MOCK_RESPONSE);
      setStreamDone(true);
      return;
    }
    setData(null);
    setExplanations({});
    setStreamDone(false);

    const controller = new AbortController();
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/recommendations/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            mode,
            keywords: keywords || null,
            limit: 20,
            candidate_pool: 200,
            explain_top: TOP_N,
            with_explanation: true,
          }),
          signal: controller.signal,
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          let detail = `HTTP ${res.status}`;
          try {
            const j = JSON.parse(text);
            detail = j.detail ?? j.error ?? detail;
          } catch {
            // 텍스트 응답이면 그대로
          }
          if (!cancelled) {
            setData({ company: null, results: [], error: detail });
            setStreamDone(true);
          }
          return;
        }
        if (!res.body) {
          if (!cancelled) setStreamDone(true);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const evt = JSON.parse(line);
              if (evt.type === "results") {
                if (!cancelled) setData(evt.data as RecommendationResponse);
              } else if (evt.type === "explanation" && evt.scope === "primary") {
                const k = `${evt.bid_ntce_no}-${evt.bid_ntce_ord}`;
                if (!cancelled)
                  setExplanations((prev) => ({ ...prev, [k]: evt.text as string }));
              } else if (evt.type === "done") {
                if (!cancelled) setStreamDone(true);
              }
            } catch {
              // 끊긴 라인은 무시
            }
          }
        }
        if (!cancelled) setStreamDone(true);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        if (!cancelled) {
          setData({
            company: null,
            results: [],
            error: (e as Error).message ?? "네트워크 오류",
          });
          setStreamDone(true);
        }
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [query, mode, useMock, keywords]);

  if (!data) {
    return <LoadingState label={query} mode={mode} />;
  }

  if (mode === "company") {
    if (data.fallback === "keywords" || !data.company) {
      return (
        <CompanyFallback
          query={query}
          company={data.company}
          message={data.error || undefined}
        />
      );
    }
    return (
      <CompanyResults
        query={query}
        keywords={keywords}
        data={data}
        explanations={explanations}
        streamDone={streamDone}
      />
    );
  }
  return (
    <KeywordResults
      query={query}
      data={data}
      explanations={explanations}
      streamDone={streamDone}
    />
  );
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

function CompanyResults({
  query,
  keywords,
  data,
  explanations,
  streamDone,
}: {
  query: string;
  keywords?: string;
  data: RecommendationResponse;
  explanations: Record<string, string>;
  streamDone: boolean;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  const subtitle = keywords
    ? `등록업종·공급물품·수주 이력 + "${keywords}" 키워드로 좁힘 · 매일 갱신 · ${today}`
    : `등록업종·공급물품·수주 이력 기준 정리 · 매일 갱신 · ${today}`;
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
            {keywords && (
              <span className="ml-2 inline-flex items-center rounded-full border border-amber-400 bg-amber-50 px-2.5 py-0.5 text-[12px] font-semibold text-amber-800 align-middle">
                + {keywords}
              </span>
            )}
          </>
        }
        subtitle={subtitle}
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
            <StreamingResultsList
              results={data.results}
              explanations={explanations}
              streamDone={streamDone}
              noResultText="조건에 맞는 공고를 찾지 못했습니다. 키워드를 넓히거나 다른 모드로 시도해보세요."
            />

            <PreSpecSection results={data.pre_spec_results ?? []} />
            <OrderPlanSection results={data.order_plan_results ?? []} />

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
  explanations,
  streamDone,
}: {
  query: string;
  data: RecommendationResponse;
  explanations: Record<string, string>;
  streamDone: boolean;
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
            <StreamingResultsList
              results={data.results}
              explanations={explanations}
              streamDone={streamDone}
              noResultText="조건에 맞는 공고를 찾지 못했습니다. 키워드를 더 구체적으로 입력하거나 다른 영역으로 시도해보세요."
              semanticHintQuery={query}
            />

            <PreSpecSection results={data.pre_spec_results ?? []} />
            <OrderPlanSection results={data.order_plan_results ?? []} />

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

function PreSpecSection({ results }: { results: PreSpecRecommendation[] }) {
  if (results.length === 0) return null;
  const top = results.slice(0, STAGE_LIMIT);
  return (
    <section className="mt-10 rounded-xl border border-amber-200 bg-amber-50/40 p-4 sm:p-5">
      <div className="flex items-baseline justify-between mb-2 px-1">
        <h3 className="text-[15.5px] sm:text-[16px] font-extrabold tracking-tight text-amber-900">
          사전규격 단계 · 골든타임
          <span className="ml-2 text-[12px] font-medium text-amber-700">
            {top.length}건
          </span>
        </h3>
        <span className="text-[11.5px] text-amber-700 font-medium">
          의견 마감 / 예산 / 유사도
        </span>
      </div>
      <p className="px-1 mb-3 text-[12px] text-amber-800/80 break-keep">
        본공고 전 사양에 의견을 낼 수 있는 시점입니다. 의견 마감일을 우선 확인하세요.
      </p>
      <div className="rounded-lg bg-white border border-amber-200 overflow-hidden divide-y divide-amber-100">
        {top.map((spec, i) => (
          <SlimPreSpecRow
            key={`prespec-${spec.bf_spec_rgst_no}`}
            spec={spec}
            rank={i + 1}
          />
        ))}
      </div>
    </section>
  );
}

function OrderPlanSection({ results }: { results: OrderPlanRecommendation[] }) {
  if (results.length === 0) return null;
  const top = results.slice(0, STAGE_LIMIT);
  return (
    <section className="mt-10">
      <div className="flex items-baseline justify-between mb-2 px-1">
        <h3 className="text-[15.5px] sm:text-[16px] font-extrabold tracking-tight text-foreground">
          발주계획 단계 · 선행지표
          <span className="ml-2 text-[12px] font-medium text-muted-foreground">
            {top.length}건
          </span>
        </h3>
        <span className="text-[11.5px] text-muted-foreground font-medium">
          발주 예정 / 예산 / 유사도
        </span>
      </div>
      <p className="px-1 mb-3 text-[12px] text-muted-foreground break-keep">
        아직 사양이 확정되지 않은 발주계획입니다. 본공고까지 1~3개월 여유 있는 사전 신호로 활용하세요.
      </p>
      <div className="rounded-lg border border-border bg-card overflow-hidden divide-y divide-border">
        {top.map((plan, i) => (
          <SlimOrderPlanRow
            key={`plan-${plan.order_plan_unty_no}`}
            plan={plan}
            rank={i + 1}
          />
        ))}
      </div>
    </section>
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
