"use client";

import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface FilterState {
  bsns_div?: string;
  region?: string;
  budget?: string;
  deadline?: string;
}

const BSNS_OPTIONS = ["전체", "용역", "물품", "공사", "외자"];
const DEADLINE_OPTIONS = ["전체", "1주일 이내", "2주일 이내", "1개월 이내"];
const BUDGET_OPTIONS = ["전체", "5천만 이하", "5천만~3억", "3억~10억", "10억 이상"];

export function FilterPanel({
  className,
  onChange,
}: {
  className?: string;
  onChange?: (filters: FilterState) => void;
}) {
  const [filters, setFilters] = useState<FilterState>({});

  const update = (key: keyof FilterState, value: string) => {
    const next = { ...filters, [key]: value === "전체" ? undefined : value };
    setFilters(next);
    onChange?.(next);
  };

  return (
    <aside className={cn("inset-card sticky top-20 p-5", className)}>
      <div className="flex items-center gap-2">
        <SlidersHorizontal className="h-3.5 w-3.5 text-ink-muted" aria-hidden />
        <span className="eyebrow text-ink">필터</span>
      </div>

      <FilterGroup
        label="업무구분"
        options={BSNS_OPTIONS}
        value={filters.bsns_div ?? "전체"}
        onSelect={(v) => update("bsns_div", v)}
      />
      <FilterGroup
        label="마감일"
        options={DEADLINE_OPTIONS}
        value={filters.deadline ?? "전체"}
        onSelect={(v) => update("deadline", v)}
      />
      <FilterGroup
        label="추정가"
        options={BUDGET_OPTIONS}
        value={filters.budget ?? "전체"}
        onSelect={(v) => update("budget", v)}
      />
    </aside>
  );
}

function FilterGroup({
  label,
  options,
  value,
  onSelect,
}: {
  label: string;
  options: string[];
  value: string;
  onSelect: (v: string) => void;
}) {
  return (
    <div className="mt-5">
      <div className="text-[12px] font-semibold text-ink-muted">{label}</div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {options.map((o) => {
          const selected = o === value;
          return (
            <button
              key={o}
              type="button"
              onClick={() => onSelect(o)}
              className={cn(
                "rounded-tile border px-2 py-1 text-[12.5px] transition-colors",
                selected
                  ? "border-navy bg-navy text-white"
                  : "border-line bg-surface text-ink-muted hover:border-line-strong hover:text-ink"
              )}
            >
              {o}
            </button>
          );
        })}
      </div>
    </div>
  );
}
