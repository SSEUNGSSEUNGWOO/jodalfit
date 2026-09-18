"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import { EmbeddingSpaceViz } from "@/components/EmbeddingSpaceViz";
import { OrderPlanSection } from "@/components/OrderPlanSection";
import { PreSpecSection } from "@/components/PreSpecSection";
import type { PeerRateStat } from "@/lib/company";
import type { RecommendationResponse } from "@/types/recommendations";

const TOP = 5;

interface Payload {
  data: RecommendationResponse;
  peer: Record<string, PeerRateStat>;
}

const H2 =
  "font-gc-serif font-black text-[22px] sm:text-[26px] tracking-[-0.02em] text-gc-ink";

/** 회사 페이지 추천 섹션 — /api/companies/[bizrno]/recommendations 를 브라우저에서 호출.
 *  SSR에 넣지 않는 이유: 백엔드 추천이 10초 이상 걸려 검색봇 크롤이 막혔다. */
export function CompanyRecommendations({
  bizrnoNorm,
  corpNm,
}: {
  bizrnoNorm: string;
  corpNm: string;
}) {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`/api/companies/${bizrnoNorm}/recommendations`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((p: Payload) => {
        if (alive) setPayload(p);
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
    };
  }, [bizrnoNorm]);

  const liveHref = `/recommendations?company=${encodeURIComponent(corpNm)}`;

  if (failed || payload?.data.error) {
    return (
      <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <h2 className={H2}>추천 공고</h2>
        <p className="mt-2 text-[14.5px] text-muted-foreground break-keep">
          추천을 불러오지 못했습니다. 실시간 조회로 바로 확인할 수 있어요.
        </p>
        <Link
          href={liveHref}
          className="mt-4 inline-flex items-center h-11 px-4 rounded-lg bg-primary text-primary-foreground text-[14px] font-bold hover:bg-primary/90 transition-colors"
        >
          {corpNm} 실시간 추천 열기 →
        </Link>
      </section>
    );
  }

  if (!payload) {
    return (
      <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <h2 className={H2}>추천 공고</h2>
        <p className="mt-1 text-[14px] text-muted-foreground">
          {corpNm}에 맞는 공고를 찾는 중이에요. 10초쯤 걸릴 수 있어요.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <div className="h-32 w-full bg-muted/60 rounded-xl animate-pulse" />
          <div className="h-32 w-full bg-muted/60 rounded-xl animate-pulse" />
        </div>
      </section>
    );
  }

  const { data, peer } = payload;
  const top = data.results.slice(0, TOP);
  const slim = data.results.slice(TOP);

  return (
    <>
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
      <PreSpecSection results={data.pre_spec_results ?? []} />

      <div className="flex items-baseline justify-between mt-10 mb-5">
        <h2 className={H2}>
          {corpNm}에 맞는 공고 {data.results.length}건
        </h2>
        <span className="text-[12.5px] text-muted-foreground font-medium">점수 순</span>
      </div>
      {data.summary && (
        <p className="mb-6 text-[14.5px] leading-[1.8] text-gc-ink-2 break-keep max-w-[72ch]">
          <b className="font-gc-serif font-black text-gc-ink text-[15.5px] mr-2">
            총평
          </b>
          {data.summary}
        </p>
      )}
      {data.results.length === 0 ? (
        <p className="text-[14.5px] text-muted-foreground break-keep">
          현재 매칭되는 신규 공고가 없어요.{" "}
          <Link href={liveHref} className="font-bold text-primary hover:underline">
            실시간 조회로 다시 확인
          </Link>
          하거나 나중에 들러보세요.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {top.map((bid, i) => (
              <BidCard
                key={`${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                bid={bid}
                rank={i + 1}
                targetBizrno={bizrnoNorm}
                peerStat={bid.dmnd_instt_nm ? peer[bid.dmnd_instt_nm] : undefined}
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
                    rank={TOP + i + 1}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <OrderPlanSection results={data.order_plan_results ?? []} />
    </section>

    {data.viz && <EmbeddingSpaceViz viz={data.viz} companyName={corpNm} />}
    </>
  );
}
