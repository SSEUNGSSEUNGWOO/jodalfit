"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import type { RecommendationResponse, BidRecommendation } from "@/types/recommendations";

const TOP_N = 5;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type StreamMode = "company" | "keywords" | "auto";

interface Props {
  query: string;
  mode: StreamMode;
  results: RecommendationResponse["results"];
  noResultText: string;
  semanticHintQuery?: string;
  /** mock 모드면 stream 호출하지 않음 (이미 explanation 포함된 응답). */
  skipStream?: boolean;
}

function bidKey(b: { bid_ntce_no: string; bid_ntce_ord: string }) {
  return `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
}

export function StreamingResultsList({
  query,
  mode,
  results,
  noResultText,
  semanticHintQuery,
  skipStream,
}: Props) {
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [streamDone, setStreamDone] = useState(false);

  useEffect(() => {
    if (skipStream || results.length === 0) {
      setStreamDone(true);
      return;
    }
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
            limit: 20,
            candidate_pool: 200,
            explain_top: TOP_N,
            with_explanation: true,
          }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) {
          setStreamDone(true);
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
              if (evt.type === "explanation" && evt.scope === "primary") {
                const k = `${evt.bid_ntce_no}-${evt.bid_ntce_ord}`;
                setExplanations((prev) => ({ ...prev, [k]: evt.text as string }));
              } else if (evt.type === "done") {
                setStreamDone(true);
              }
            } catch {
              // 무시 — 끊긴 라인일 수 있음
            }
          }
        }
        setStreamDone(true);
      } catch {
        setStreamDone(true);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [query, mode, results, skipStream]);

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
