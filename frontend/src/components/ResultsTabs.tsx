"use client";

import { useState } from "react";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import { cn } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";

const TOP_N = 5;

interface Props {
  initial: "company" | "keywords";
  companyAvailable: boolean;
  keywordAvailable: boolean;
  companyCount: number;
  keywordCount: number;
  query: string;
  companyResults: BidRecommendation[];
  keywordResults: BidRecommendation[];
}

export function ResultsTabs({
  initial,
  companyAvailable,
  keywordAvailable,
  companyCount,
  keywordCount,
  query,
  companyResults,
  keywordResults,
}: Props) {
  const [tab, setTab] = useState<"company" | "keywords">(initial);

  const tabs: { id: "company" | "keywords"; label: string; sub: string; available: boolean; count: number }[] = [
    {
      id: "company",
      label: "회사 기준",
      sub: "등록업종·공급물품·수주 이력",
      available: companyAvailable,
      count: companyCount,
    },
    {
      id: "keywords",
      label: "키워드 기준",
      sub: "공고 의미 유사도",
      available: keywordAvailable,
      count: keywordCount,
    },
  ];

  const activeResults = tab === "company" ? companyResults : keywordResults;
  const sortLabel = tab === "company" ? "점수 순" : "유사도 순";

  return (
    <div>
      <div className="flex items-stretch gap-1 border-b border-border mb-6">
        {tabs.map((t) => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              disabled={!t.available}
              onClick={() => t.available && setTab(t.id)}
              className={cn(
                "relative px-4 sm:px-5 py-3 text-left transition-colors",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                isActive
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <div className="flex items-center gap-2">
                <span className="text-[15px] font-bold">{t.label}</span>
                {t.available && (
                  <span
                    className={cn(
                      "tabular-nums text-[11.5px] font-bold px-1.5 py-0.5 rounded",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {t.count}
                  </span>
                )}
              </div>
              <div className="mt-0.5 text-[12px] text-muted-foreground">
                {t.sub}
              </div>
              {isActive && (
                <span className="absolute left-0 right-0 -bottom-px h-[3px] bg-primary rounded-t-sm" />
              )}
            </button>
          );
        })}
        <div className="flex-1" />
      </div>

      <div className="flex items-baseline justify-between mb-5">
        <h2 className="text-[20px] sm:text-[22px] font-extrabold tracking-tight text-foreground">
          {tab === "company" ? (
            <>
              회사에 맞는 공고 {activeResults.length}건
            </>
          ) : (
            <>
              <span className="font-serif italic">“{query}”</span> 관련 공고 {activeResults.length}건
            </>
          )}
        </h2>
        <span className="text-[12.5px] text-muted-foreground font-medium">
          {sortLabel}
        </span>
      </div>

      {activeResults.length === 0 ? (
        <div className="rounded-xl bg-muted/40 border border-border p-8 text-center">
          <h3 className="text-[18px] font-bold text-foreground">
            이 기준으로 찾은 공고가 없어요.
          </h3>
          <p className="mt-2 text-[14px] text-muted-foreground">
            다른 탭을 확인하거나 검색어를 바꿔보세요.
          </p>
        </div>
      ) : (
        <>
          {/* TOP 5 큰 카드 */}
          <div className="flex flex-col gap-4">
            {activeResults.slice(0, TOP_N).map((bid, i) => (
              <BidCard
                key={`${tab}-${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                bid={bid}
                rank={i + 1}
              />
            ))}
          </div>

          {/* 6~20 슬림 리스트 */}
          {activeResults.length > TOP_N && (
            <section className="mt-10">
              <div className="flex items-baseline justify-between mb-3 px-3">
                <h3 className="text-[15px] font-bold text-foreground">
                  관련 공고 {activeResults.length - TOP_N}개 더
                </h3>
                <span className="text-[11.5px] text-muted-foreground font-medium">
                  점수 / 마감 / 예산
                </span>
              </div>
              <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
                {activeResults.slice(TOP_N).map((bid, i) => (
                  <SlimBidRow
                    key={`${tab}-slim-${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                    bid={bid}
                    rank={TOP_N + i + 1}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
