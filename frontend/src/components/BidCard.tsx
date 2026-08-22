import Link from "next/link";
import { ArrowUpRight, BarChart3, Sparkles } from "lucide-react";
import { SaveBidButton } from "@/components/SaveBidButton";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { DDayBadge } from "./DDayBadge";
import { EvidenceTag } from "./EvidenceTag";
import { ExplanationBlock } from "./ExplanationBlock";
import { MatchScore } from "./MatchScore";
import { cn, formatKRW } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";
import type { GoldenTimeInfo } from "@/lib/golden-time";
import type { PeerRateStat } from "@/lib/company";

export function BidCard({
  bid,
  rank,
  preview = false,
  className,
  semanticHintQuery,
  golden,
  peerStat,
  targetBizrno = null,
}: {
  bid: BidRecommendation;
  rank?: number;
  preview?: boolean;
  className?: string;
  /** 어느 회사 페이지에서 본 카드인지 — 저장 이벤트 로깅에 함께 남긴다 */
  targetBizrno?: string | null;
  /** 키워드 모드에서 의미 매칭을 강조하기 위한 검색어. 검색어가 공고명/업종에 직접 포함되지 않으면 "의미 매칭" 배지 표시 */
  semanticHintQuery?: string;
  /** 골든타임(사전규격공개) 정보. spec_open/spec_closing일 때만 뱃지 노출 */
  golden?: GoldenTimeInfo;
  /** 같은 발주기관의 과거 낙찰 평균 투찰율 (n>=3일 때만 카드에 표시) */
  peerStat?: PeerRateStat;
}) {
  const isGolden =
    golden?.status === "spec_open" || golden?.status === "spec_closing";
  const isGoldenClosing = golden?.status === "spec_closing";
  const tokens = (semanticHintQuery ?? "")
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length >= 2);
  const haystack = (
    (bid.bid_ntce_nm ?? "") +
    " " +
    (bid.bidprc_psbl_indstryty_nm ?? "")
  ).toLowerCase();
  const isSemanticOnly =
    tokens.length > 0 && !tokens.some((t) => haystack.includes(t));
  return (
    <Card
      className={cn(
        "overflow-hidden transition-shadow gap-0 py-0",
        preview ? "shadow-lg" : "hover:shadow-md",
        className
      )}
    >
      <CardContent className="p-6 sm:p-7">
        {/* Top: rank + meta + score */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
            {rank !== undefined && (
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-[12.5px] font-extrabold tabular tabular-nums shrink-0">
                {rank}
              </span>
            )}
            <Badge variant="secondary" className="bg-primary/10 text-primary font-semibold">
              {bid.bsns_div_nm || "공고"}
            </Badge>
            {isGolden && (
              <Badge
                className={cn(
                  "font-bold gap-1",
                  isGoldenClosing
                    ? "bg-amber-500 text-white hover:bg-amber-500"
                    : "bg-amber-100 text-amber-900 hover:bg-amber-100 border border-amber-300"
                )}
                title={
                  isGoldenClosing
                    ? "사전규격 의견 마감 임박 — 사양 반영 마지막 기회"
                    : "사전규격 공개중 — 의견 등록 가능"
                }
              >
                <Sparkles className="h-3 w-3" strokeWidth={2.5} />
                {golden?.opinionDaysLeft !== null && golden?.opinionDaysLeft !== undefined
                  ? golden.opinionDaysLeft === 0
                    ? "골든타임 마감 오늘"
                    : `골든타임 D-${golden.opinionDaysLeft}`
                  : "골든타임"}
              </Badge>
            )}
            {isSemanticOnly && (
              <Badge
                variant="outline"
                className="text-[11px] font-bold border-primary/40 text-primary"
                title={`검색어 "${semanticHintQuery}"가 공고에 직접 들어가지 않지만 의미가 가까워서 매칭됐어요`}
              >
                ✨ 의미 매칭
              </Badge>
            )}
            <span className="hidden sm:inline text-xs tabular tabular-nums text-muted-foreground">
              {bid.bid_ntce_no}
            </span>
          </div>
          <MatchScore score={bid.score} size="sm" className="shrink-0" />
        </div>

        {/* Title — links to lifecycle page */}
        <h3 className="mt-4 text-[20px] sm:text-[22px] font-extrabold tracking-tight leading-[1.35]">
          <Link
            href={`/notices/${bid.bid_ntce_no}`}
            className="text-foreground hover:text-primary transition-colors"
          >
            {bid.bid_ntce_nm}
          </Link>
        </h3>

        {/* Meta */}
        <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13.5px] text-muted-foreground">
          <span className="font-semibold text-foreground/80">
            {bid.dmnd_instt_nm || bid.ntce_instt_nm || "—"}
          </span>
          {bid.prtcpt_psbl_rgn_nm && (
            <>
              <Dot />
              <span>{bid.prtcpt_psbl_rgn_nm}</span>
            </>
          )}
          {bid.bidprc_psbl_indstryty_nm && (
            <>
              <Dot />
              <span className="truncate max-w-[240px]">
                {bid.bidprc_psbl_indstryty_nm}
              </span>
            </>
          )}
        </div>

        {/* Explanation */}
        {bid.explanation && (
          <div className="mt-5">
            <ExplanationBlock text={bid.explanation} />
          </div>
        )}

        {/* Evidence */}
        {bid.evidence && bid.evidence.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            {bid.evidence.map((tag) => (
              <EvidenceTag key={tag}>{tag}</EvidenceTag>
            ))}
          </div>
        )}

        {/* Peer 통계 — 같은 발주기관 과거 낙찰 평균 투찰율 (n>=3) */}
        {peerStat && peerStat.n >= 3 && (
          <div
            className="mt-4 inline-flex items-center gap-1.5 text-[12.5px] text-muted-foreground"
            title="같은 발주기관의 과거 낙찰 평균 투찰율 — 참고용 시그널이지 예측치 아님"
          >
            <BarChart3 className="h-3.5 w-3.5 text-primary/70" aria-hidden />
            <span>
              이 기관 비슷한 공고{" "}
              <span className="font-bold text-foreground">
                평균 {peerStat.avg.toFixed(1)}%
              </span>{" "}
              <span className="tabular tabular-nums">(n={peerStat.n})</span>
            </span>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex flex-wrap items-center justify-between gap-3 bg-muted/40 border-t px-6 sm:px-7 py-3.5">
        <div className="flex items-center gap-4">
          <DDayBadge date={bid.bid_clse_date} />
          <div className="flex items-baseline gap-1.5">
            <span className="text-[12px] font-semibold text-muted-foreground">
              추정가
            </span>
            <span className="text-[15px] font-bold tabular tabular-nums text-foreground">
              {formatKRW(bid.presmpt_prce)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <SaveBidButton bid={bid} rank={rank} targetBizrno={targetBizrno} />
          {/*
            카드의 주 버튼("공고 보기")은 나라장터로 내보낸다. 우리 라이프사이클
            페이지(발주계획→사전규격→개찰→계약)로 가는 길이 하나도 없어서 이 자리를
            내부 상세로 연결한다. 회사 → 공고 내부 링크가 생기는 효과도 있다.
          */}
          <Link
            href={`/notices/${bid.bid_ntce_no}`}
            aria-label="공고 상세 보기"
            className={buttonVariants({ variant: "ghost", size: "icon" })}
          >
            <BarChart3 className="h-4 w-4" />
          </Link>
          {bid.bid_ntce_url && (
            <a
              href={bid.bid_ntce_url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "ml-1 inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg",
                "bg-primary text-primary-foreground text-sm font-bold",
                "hover:bg-primary/90 transition-colors"
              )}
            >
              공고 보기
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}

function Dot() {
  return (
    <span aria-hidden className="text-muted-foreground/50">
      ·
    </span>
  );
}
