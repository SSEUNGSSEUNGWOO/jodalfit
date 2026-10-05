"use client";

import { Sparkles } from "lucide-react";
import { analyzeGoldenTimeFromParts, isGoldenTime } from "@/lib/golden-time";
import type { LifecycleData } from "@/lib/lifecycle-data";
import { useToday } from "@/lib/use-today";
import { formatDateKR } from "@/lib/utils";

/** 공고 상세 상단 골든타임 띠. 오늘 날짜가 있어야 판정할 수 있으므로 브라우저에서만 그린다 —
 *  서버가 구운 HTML에는 들어가지 않는다 (use-today.ts 참조). */
export function GoldenTimeBanner({ data }: { data: LifecycleData }) {
  const today = useToday();
  if (!today) return null;

  const gt = analyzeGoldenTimeFromParts(
    {
      notice: data.notice,
      preSpecs: data.preSpecs,
      opinionCount: data.opinionCount,
      hasAwardsOrContracts: data.awards.length > 0 || data.contracts.length > 0,
      hasOrderPlans: data.orderPlans.length > 0,
    },
    today
  );
  if (!isGoldenTime(gt.status)) return null;
  const specPdfUrl = data.preSpecs[0]?.spec_doc_file_url_1;

  return (
    <div className="bg-amber-500 text-white">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13.5px] font-semibold">
        <span className="inline-flex items-center gap-1.5">
          <Sparkles className="h-4 w-4" strokeWidth={2.5} />
          <span className="font-extrabold tracking-tight">골든타임</span>
        </span>
        <span className="text-white/90">
          {gt.opinionDaysLeft !== null
            ? gt.opinionDaysLeft === 0
              ? "오늘이 의견 등록 마감일이에요"
              : `의견 등록 마감 D-${gt.opinionDaysLeft}`
            : "사전규격 공개 중 — 의견을 등록할 수 있어요"}
          {gt.opinionDeadline && (
            <span className="ml-1.5 text-white/70 font-medium">
              ({formatDateKR(gt.opinionDeadline)})
            </span>
          )}
        </span>
        {gt.opinionCount > 0 && (
          <span className="text-white/80">
            · 의견 {gt.opinionCount}건 등록됨
          </span>
        )}
        {specPdfUrl && (
          <a
            href={specPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto inline-flex items-center gap-1 rounded-md bg-white/15 hover:bg-white/25 px-2.5 py-1 text-[12.5px] font-bold transition-colors"
          >
            사양서 PDF 보기
          </a>
        )}
      </div>
    </div>
  );
}
