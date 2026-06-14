"use client";

import { Loader2 } from "lucide-react";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import type { RecommendationResponse, BidRecommendation } from "@/types/recommendations";

const TOP_N = 5;

interface Props {
  results: RecommendationResponse["results"];
  explanations: Record<string, string>;
  streamDone: boolean;
  noResultText: string;
  semanticHintQuery?: string;
}

function bidKey(b: { bid_ntce_no: string; bid_ntce_ord: string }) {
  return `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
}

export function StreamingResultsList({
  results,
  explanations,
  streamDone,
  noResultText,
  semanticHintQuery,
}: Props) {
  if (results.length === 0) {
    return (
      <div className="rounded-xl bg-muted/40 border border-border p-8 text-center">
        <h3 className="text-[18px] font-bold text-foreground">{noResultText}</h3>
      </div>
    );
  }

  const top = results.slice(0, TOP_N);
  const slim = results.slice(TOP_N);

  const withExplanation = (b: BidRecommendation): BidRecommendation => {
    const k = bidKey(b);
    if (explanations[k]) return { ...b, explanation: explanations[k] };
    return b;
  };

  return (
    <>
      <div className="flex flex-col gap-4">
        {top.map((bid, i) => {
          const filled = withExplanation(bid);
          const pending = !filled.explanation && !streamDone;
          return (
            <div key={bidKey(bid)} className="relative">
              <BidCard
                bid={filled}
                rank={i + 1}
                semanticHintQuery={semanticHintQuery}
              />
              {pending && (
                <div className="mt-2 flex items-center gap-2 px-4 text-[12px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                  AI가 매칭 이유 분석 중…
                </div>
              )}
            </div>
          );
        })}
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
                key={`slim-${bidKey(bid)}`}
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
