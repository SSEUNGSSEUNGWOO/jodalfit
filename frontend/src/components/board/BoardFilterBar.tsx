"use client";

import { cn } from "@/lib/utils";

export interface BoardFilters {
  /** 업무구분 (bsns_div_nm 원문값). undefined = 전체 */
  div?: string;
  /** 마감일 상한 (일). undefined = 전체 */
  deadline?: number;
  /** 추정가 [min, max) 원. undefined = 전체 */
  budget?: [number, number | null];
  /** 저장(검토 인장)만 보기 */
  savedOnly: boolean;
}

export const EMPTY_FILTERS: BoardFilters = { savedOnly: false };

export const DEADLINE_OPTIONS: { label: string; value: number }[] = [
  { label: "7일 이내", value: 7 },
  { label: "14일 이내", value: 14 },
  { label: "30일 이내", value: 30 },
];

export const BUDGET_OPTIONS: { label: string; value: [number, number | null] }[] = [
  { label: "5천만 이하", value: [0, 50_000_000] },
  { label: "5천만~3억", value: [50_000_000, 300_000_000] },
  { label: "3억~10억", value: [300_000_000, 1_000_000_000] },
  { label: "10억 이상", value: [1_000_000_000, null] },
];

export function isFiltered(f: BoardFilters) {
  return !!(f.div || f.deadline || f.budget || f.savedOnly);
}

/** 조회 조건 바 — 실제로 목록을 거르는 캡슐 컨트롤. 선택 시 인주 점이 앞으로 온다. */
export function BoardFilterBar({
  filters,
  onChange,
  divOptions,
  savedCount,
  shownCount,
  totalCount,
  className,
}: {
  filters: BoardFilters;
  onChange: (f: BoardFilters) => void;
  /** 결과에 실제 존재하는 업무구분 값들 */
  divOptions: string[];
  savedCount: number;
  shownCount: number;
  totalCount: number;
  className?: string;
}) {
  const filtered = isFiltered(filters);

  return (
    <div
      className={cn(
        "border-y border-gc-rule bg-gc-paper/95 backdrop-blur-sm",
        className
      )}
    >
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 py-2.5 flex items-center gap-4">
        <div className="flex-1 min-w-0 flex items-center gap-x-4 gap-y-2 overflow-x-auto [scrollbar-width:thin] sm:flex-wrap sm:overflow-visible">
        <Group label="구분">
          {divOptions.map((d) => (
            <Capsule
              key={d}
              active={filters.div === d}
              onClick={() =>
                onChange({ ...filters, div: filters.div === d ? undefined : d })
              }
            >
              {d}
            </Capsule>
          ))}
        </Group>

        <Divider />

        <Group label="마감">
          {DEADLINE_OPTIONS.map((o) => (
            <Capsule
              key={o.value}
              active={filters.deadline === o.value}
              onClick={() =>
                onChange({
                  ...filters,
                  deadline: filters.deadline === o.value ? undefined : o.value,
                })
              }
            >
              {o.label}
            </Capsule>
          ))}
        </Group>

        <Divider />

        <Group label="추정가">
          {BUDGET_OPTIONS.map((o) => (
            <Capsule
              key={o.label}
              active={filters.budget?.[0] === o.value[0]}
              onClick={() =>
                onChange({
                  ...filters,
                  budget:
                    filters.budget?.[0] === o.value[0] ? undefined : o.value,
                })
              }
            >
              {o.label}
            </Capsule>
          ))}
        </Group>

        {savedCount > 0 && (
          <>
            <Divider />
            <Capsule
              active={filters.savedOnly}
              stamp
              onClick={() =>
                onChange({ ...filters, savedOnly: !filters.savedOnly })
              }
            >
              검토 인장 {savedCount}
            </Capsule>
          </>
        )}

        </div>

        {/* 카운트·해제 — 스크롤 영역 밖 고정 (모바일에서도 항상 보임) */}
        <span className="shrink-0 flex items-center gap-2.5 text-[12px] tabular tabular-nums text-gc-ink-3">
          {filtered ? (
            <>
              <span className="whitespace-nowrap">
                {totalCount}건 중 <b className="text-gc-ink font-bold">{shownCount}건</b>
              </span>
              <button
                type="button"
                onClick={() => onChange(EMPTY_FILTERS)}
                className="whitespace-nowrap font-bold text-gc-ink underline underline-offset-2 hover:text-gc-ink-2"
              >
                조건 해제
              </button>
            </>
          ) : (
            <span className="whitespace-nowrap">{totalCount}건 전체</span>
          )}
        </span>
      </div>
    </div>
  );
}

function Group({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-1.5 shrink-0" role="group" aria-label={label}>
      <span className="text-[11.5px] font-bold text-gc-ink-2 mr-0.5">{label}</span>
      {children}
    </div>
  );
}

function Divider() {
  return <span aria-hidden className="h-4 w-px bg-gc-rule shrink-0" />;
}

function Capsule({
  active,
  stamp,
  onClick,
  children,
}: {
  active: boolean;
  stamp?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 h-7 px-3 rounded-full border text-[12.5px] font-semibold whitespace-nowrap transition-colors shrink-0",
        active
          ? "bg-gc-ink text-gc-paper border-gc-ink"
          : "bg-gc-sheet text-gc-ink-2 border-gc-rule hover:border-gc-ink-2"
      )}
    >
      {active && (
        <span
          aria-hidden
          className={cn(
            "inline-block size-1.5 rounded-full",
            stamp ? "bg-gc-injuk" : "bg-gc-tint"
          )}
        />
      )}
      {children}
    </button>
  );
}
