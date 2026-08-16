"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { ReviewStamp } from "@/components/board/BoardSeal";
import { cn, daysUntil, formatDateKR, formatKRW, scoreLabel, scorePercent } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";

export function bidKey(b: { bid_ntce_no: string; bid_ntce_ord: string }) {
  return `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
}

/** 마감 표기 — 원천 데이터 이상치(D-2960 등)는 날짜로 강등 */
function Deadline({ date, compact }: { date: string | null; compact?: boolean }) {
  const d = daysUntil(date);
  if (d === null) return <span className="text-gc-ink-3">—</span>;
  if (d < 0) return <span className="text-gc-ink-3">마감</span>;
  if (d > 60)
    return (
      <span className="text-gc-ink-3 tabular tabular-nums">
        ~{formatDateKR(date).slice(compact ? 5 : 0)}
      </span>
    );
  const label = d === 0 ? "오늘" : `D-${d}`;
  return (
    <span
      className={cn(
        "tabular tabular-nums font-bold",
        d <= 2 ? "text-gc-injuk" : d <= 5 ? "text-gc-amber" : "text-gc-ink"
      )}
    >
      {label}
    </span>
  );
}

function FitLabel({ score, compact }: { score: number; compact?: boolean }) {
  const { label, tone } = scoreLabel(score);
  return (
    <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
      <span
        className={cn(
          "font-bold",
          compact ? "text-[13px]" : "text-[14px]",
          tone === "primary" ? "text-gc-ink" : "text-gc-ink-3"
        )}
      >
        {label}
      </span>
      <span className="text-[12px] tabular tabular-nums text-gc-ink-3">
        {scorePercent(score)}
      </span>
    </span>
  );
}

export interface BoardRowProps {
  bid: BidRecommendation;
  rank: number;
  open: boolean;
  onToggle: () => void;
  saved: boolean;
  onToggleSave: () => void;
  /** 상위 N건 — LLM 설명 대상 */
  primary: boolean;
  explanationPending: boolean;
}

/** 개찰판의 행 하나. 행 전체가 개봉 토글, 개봉부에 근거·인장·원문 링크. */
export function BoardRow({
  bid,
  rank,
  open,
  onToggle,
  saved,
  onToggleSave,
  primary,
  explanationPending,
}: BoardRowProps) {
  const panelId = `gc-open-${bidKey(bid)}`;
  const instt = bid.dmnd_instt_nm || bid.ntce_instt_nm || "—";
  const signals = (bid.score_breakdown ?? []).filter((s) => s.key !== "vector");
  const industries = dedupeIndustries(bid.bidprc_psbl_indstryty_nm);

  return (
    <li className="border-b border-gc-rule last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
        className={cn(
          "relative w-full text-left grid items-baseline gap-x-4 px-1 py-3.5 sm:py-4 transition-colors",
          "grid-cols-[40px_minmax(0,1fr)_28px] sm:grid-cols-[48px_minmax(0,1fr)_84px_104px_120px_28px]",
          open ? "bg-gc-sheet" : "hover:bg-gc-sheet/60"
        )}
      >
        {/* 봉인 딱지 — 닫힌 행의 아래 괘선(개봉될 이음선)을 덮고 있다가 개봉되면 사라짐 */}
        {!open && (
          <span
            aria-hidden
            className="absolute right-9 sm:right-12 bottom-0 translate-y-1/2 h-[17px] w-[11px] rounded-[1px] bg-gc-band"
          />
        )}
        {/* 순번 + 인장 */}
        <span className="relative self-start text-right pr-1">
          <span className="text-[15px] font-bold tabular tabular-nums text-gc-ink-2">
            {String(rank).padStart(2, "0")}
          </span>
          {saved && (
            <ReviewStamp className="gc-stamp-in absolute -top-1.5 -left-2 pointer-events-none" />
          )}
        </span>

        {/* 공고명 + 기관 */}
        <span className="min-w-0">
          <span
            className={cn(
              "block text-[15.5px] sm:text-[16.5px] font-bold leading-[1.45] text-gc-ink break-keep",
              !open && "sm:truncate sm:whitespace-nowrap"
            )}
          >
            {bid.bid_ntce_nm}
          </span>
          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px] text-gc-ink-3">
            <span className="font-semibold text-gc-ink-2">{instt}</span>
            {bid.bsns_div_nm && (
              <span className="border border-gc-rule rounded-[3px] px-1.5 py-px text-[11.5px] font-semibold text-gc-ink-2 bg-gc-sheet">
                {bid.bsns_div_nm}
              </span>
            )}
            {bid.prtcpt_psbl_rgn_nm && <span>{bid.prtcpt_psbl_rgn_nm}</span>}
            {/* 모바일 전용 수치 라인 */}
            <span className="sm:hidden inline-flex items-center gap-2 tabular tabular-nums">
              <Deadline date={bid.bid_clse_date} compact />
              <span className="text-gc-ink-2 font-semibold">
                {formatKRW(bid.presmpt_prce)}
              </span>
              <FitLabel score={bid.score} compact />
            </span>
          </span>
        </span>

        {/* 데스크톱 수치 컬럼 — 공유 괘선 정렬 */}
        <span className="hidden sm:block text-right text-[14px] self-start">
          <Deadline date={bid.bid_clse_date} />
        </span>
        <span className="hidden sm:block text-right text-[14px] font-semibold tabular tabular-nums text-gc-ink self-start">
          {formatKRW(bid.presmpt_prce)}
        </span>
        <span className="hidden sm:block text-right self-start">
          <FitLabel score={bid.score} />
        </span>

        <span className="self-start justify-self-end text-gc-ink-3" aria-hidden>
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform duration-300",
              open && "rotate-180"
            )}
          />
        </span>
      </button>

      {/* 개봉부 */}
      <div className="gc-open-wrap" data-open={open} id={panelId}>
        <div className="gc-open-inner">
          {/* 절취선 — 개봉된 봉투의 뜯긴 자리 */}
          <div className="mx-1 mb-4 border-t border-dashed border-gc-tint-line bg-gc-sheet px-4 sm:px-6 py-4 sm:py-5">
            {/* 추천 근거 */}
            {bid.explanation ? (
              <p className="text-[14px] leading-[1.75] text-gc-ink-2 break-keep">
                <b className="text-gc-ink font-bold mr-1.5">추천 근거</b>
                {bid.explanation}
              </p>
            ) : primary && explanationPending ? (
              <p className="text-[13px] text-gc-ink-3">근거 작성 중…</p>
            ) : null}

            {/* 시그널 · 증거 */}
            {(signals.length > 0 || (bid.evidence?.length ?? 0) > 0) && (
              <div className="mt-3.5 flex flex-wrap gap-1.5">
                {signals.map((s) => (
                  <span
                    key={s.key}
                    className={cn(
                      "inline-flex items-center border rounded-[3px] px-2 py-0.5 text-[12px] font-semibold",
                      s.points > 0
                        ? "border-gc-tint-line bg-gc-tint text-gc-tint-ink"
                        : s.points < 0
                          ? "border-gc-rule bg-gc-paper text-gc-ink-3"
                          : "border-gc-rule bg-gc-sheet text-gc-ink-3"
                    )}
                  >
                    {s.points < 0 && <span aria-hidden className="mr-0.5">−</span>}
                    {s.label}
                  </span>
                ))}
                {(bid.evidence ?? []).map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center border border-gc-tint-line bg-gc-tint rounded-[3px] px-2 py-0.5 text-[12px] font-semibold text-gc-tint-ink"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* 자격 판정 */}
            {bid.qualification && bid.qualification.reasons.length > 0 && (
              <p className="mt-3 text-[12.5px] text-gc-ink-3 break-keep">
                <span aria-hidden>※ </span>
                자격 확인: {bid.qualification.reasons.join(" · ")}
              </p>
            )}

            {/* 업종 (중복 정리) */}
            {industries.length > 0 && (
              <p className="mt-1.5 text-[12.5px] text-gc-ink-3 break-keep">
                <span aria-hidden>※ </span>
                투찰 가능 업종: {industries.slice(0, 4).join(" · ")}
                {industries.length > 4 && ` 외 ${industries.length - 4}종`}
              </p>
            )}

            {/* 액션 */}
            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              <button
                type="button"
                onClick={onToggleSave}
                aria-pressed={saved}
                className={cn(
                  "inline-flex items-center gap-1.5 h-9 px-3.5 rounded-[3px] border text-[13.5px] font-bold transition-colors",
                  saved
                    ? "border-gc-injuk bg-gc-injuk-soft text-gc-injuk-deep"
                    : "border-gc-injuk text-gc-injuk hover:bg-gc-injuk-soft"
                )}
              >
                {saved ? "검토 인장 해제" : "검토 인장 찍기"}
              </button>
              <Link
                href={`/notices/${bid.bid_ntce_no}`}
                className="inline-flex items-center gap-1 h-9 px-3.5 rounded-[3px] border border-gc-ink-2 text-[13.5px] font-bold text-gc-ink hover:bg-gc-paper transition-colors"
              >
                상세 분석
              </Link>
              {bid.bid_ntce_url && (
                <a
                  href={bid.bid_ntce_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 h-9 px-3.5 rounded-[3px] bg-gc-band text-gc-band-hi text-[13.5px] font-bold hover:bg-gc-ink transition-colors"
                >
                  나라장터 원문
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
                </a>
              )}
              <span className="ml-auto text-[11.5px] tabular tabular-nums text-gc-ink-3">
                공고번호 {bid.bid_ntce_no}
              </span>
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}

/** 원천 데이터의 업종 문자열 중복(동일 업종 16회 나열 등) 정리 */
function dedupeIndustries(raw: string | null): string[] {
  if (!raw) return [];
  return [...new Set(raw.split(/[,;/]/).map((s) => s.trim()).filter(Boolean))];
}
