import { ExternalLink, Bookmark, BarChart3 } from "lucide-react";
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
    <article
      className={cn(
        "group relative bg-surface border border-line rounded-card transition-colors hover:border-line-strong",
        preview ? "shadow-[0_24px_48px_-32px_rgba(18,53,91,0.18)]" : "",
        className
      )}
    >
      {/* Rank ribbon — editorial mark, top-left */}
      {rank !== undefined && (
        <div className="absolute -top-3 left-6 z-10">
          <span className="inline-flex items-center gap-1 rounded-tile bg-navy px-2.5 py-1 text-[11px] font-bold tracking-[0.12em] text-white">
            <span className="text-teal-300">#</span>
            <span className="tabular">{rank}</span>
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-x-6 px-6 pt-6 pb-5 sm:grid-cols-[1fr_auto] sm:items-start sm:gap-x-8 sm:px-8 sm:pt-7">
        {/* Title + meta */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="eyebrow text-navy">{bid.bsns_div_nm}</span>
            <span className="text-[11px] text-ink-soft">·</span>
            <span className="text-[12px] tabular text-ink-muted">
              {bid.bid_ntce_no}
            </span>
          </div>
          <h3 className="mt-2 text-[19px] font-semibold leading-[1.4] tracking-tight text-ink-strong sm:text-[21px]">
            {bid.bid_ntce_nm}
          </h3>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13.5px] text-ink-muted">
            <span className="text-ink">{bid.dmnd_instt_nm || bid.ntce_instt_nm || "—"}</span>
            {bid.prtcpt_psbl_rgn_nm && (
              <>
                <Separator />
                <span>{bid.prtcpt_psbl_rgn_nm}</span>
              </>
            )}
            {bid.bidprc_psbl_indstryty_nm && (
              <>
                <Separator />
                <span className="truncate max-w-[260px]">
                  {bid.bidprc_psbl_indstryty_nm}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Match score — right column on desktop */}
        <div className="mt-5 sm:mt-0">
          <MatchScore score={bid.score} size="md" />
        </div>
      </div>

      {/* Explanation block */}
      {bid.explanation && (
        <div className="px-6 pb-5 sm:px-8">
          <ExplanationBlock text={bid.explanation} />
        </div>
      )}

      {/* Evidence tags */}
      {bid.evidence && bid.evidence.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 px-6 pb-5 sm:px-8">
          {bid.evidence.map((tag) => (
            <EvidenceTag key={tag}>{tag}</EvidenceTag>
          ))}
        </div>
      )}

      {/* Bottom row: dday + price + ctas */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-bg-alt/40 px-6 py-3 sm:px-8 rounded-b-card">
        <div className="flex items-center gap-3">
          <DDayBadge date={bid.bid_clse_date} />
          <span className="text-[12px] text-ink-muted">
            <span className="eyebrow mr-1">추정가</span>
            <span className="font-semibold tabular text-ink">
              {formatKRW(bid.presmpt_prce)}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-tile px-2 py-1.5 text-[12.5px] font-medium text-ink-muted transition-colors hover:bg-line-soft hover:text-ink"
            aria-label="관심 공고 저장"
          >
            <Bookmark className="h-3.5 w-3.5" aria-hidden /> 저장
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-tile px-2 py-1.5 text-[12.5px] font-medium text-ink-muted transition-colors hover:bg-line-soft hover:text-ink"
            aria-label="상세 분석"
          >
            <BarChart3 className="h-3.5 w-3.5" aria-hidden /> 상세
          </button>
          {bid.bid_ntce_url && (
            <a
              href={bid.bid_ntce_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-tile bg-navy px-3 py-1.5 text-[12.5px] font-semibold text-white transition-colors hover:bg-navy-700"
            >
              공고 원문 <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

function Separator() {
  return <span className="text-ink-soft text-[11px]" aria-hidden>·</span>;
}
