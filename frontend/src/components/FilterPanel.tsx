"use client";

import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface FilterState {
  bsns_div?: string;
  budget?: string;
  deadline?: string;
}

const BSNS_OPTIONS = ["전체", "용역", "물품", "공사", "외자"];
const DEADLINE_OPTIONS = ["전체", "1주일 이내", "2주일 이내", "1개월 이내"];
const BUDGET_OPTIONS = ["전체", "5천만 이하", "5천~3억", "3억~10억", "10억 이상"];

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
    <Card className={cn("sticky top-24", className)}>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" aria-hidden />
          <span className="text-sm font-bold text-foreground">필터</span>
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
      </CardContent>
    </Card>
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
    <div className="mt-4 pt-4 border-t first:border-t-0 first:mt-0 first:pt-0">
      <div className="text-xs font-bold text-muted-foreground mb-2.5">
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const selected = o === value;
          return (
            <Button
              key={o}
              size="sm"
              variant={selected ? "default" : "secondary"}
              onClick={() => onSelect(o)}
              className="h-7 px-3 text-[12.5px] font-semibold"
            >
              {o}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
