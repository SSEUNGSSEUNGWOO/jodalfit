import Link from "next/link";
import { ArrowUpRight, Bookmark, BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { DDayBadge } from "./DDayBadge";
import { EvidenceTag } from "./EvidenceTag";
import { ExplanationBlock } from "./ExplanationBlock";
import { MatchScore } from "./MatchScore";
import { cn, formatKRW } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";

export function BidCard({
  bid,
  rank,
  preview = false,
  className,
}: {
  bid: BidRecommendation;
  rank?: number;
  preview?: boolean;
  className?: string;
}) {
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
          <Button variant="ghost" size="icon" aria-label="저장">
            <Bookmark className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="상세">
            <BarChart3 className="h-4 w-4" />
          </Button>
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
