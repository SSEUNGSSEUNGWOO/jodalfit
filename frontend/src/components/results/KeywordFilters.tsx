// frontend/src/components/results/KeywordFilters.tsx
// 키워드 모드 좁히기 — 구분(물품·용역·공사)·마감(7일·30일 이내). 칩은 링크라 주소(div·due)가 바뀌고 페이지가 다시 계산한다.
// 글자 일치가 상한 300 에 잘리기 전에 조회 조건으로 걸려야 해서 화면에서 거르지 않는다(backend _search_title_matches). 2026-10-28.
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { KeywordFilter } from "@/types/recommendations";

const DIVS = ["물품", "용역", "공사"] as const;
const DUES = [[7, "7일 이내"], [30, "30일 이내"]] as const;
const CHIP = "num cursor-pointer border-b pb-px text-[13px] transition-colors";

export function KeywordFilters({ query, from, filter }: { query: string; from: string | null; filter: KeywordFilter }) {
  const href = (next: KeywordFilter) => {
    const p = new URLSearchParams({ q: query });
    if (from) p.set("from", from);
    if (next.div) p.set("div", next.div);
    if (next.due) p.set("due", String(next.due));
    return `/recommendations?${p.toString()}`;
  };
  const chip = (on: boolean, to: KeywordFilter, label: string) => (
    <Link key={label} href={href(to)} aria-current={on ? "true" : undefined}
      className={cn(CHIP, on ? "border-orange font-[650] text-ink" : "border-transparent text-ink-g hover:border-field hover:text-ink")}>{label}</Link>
  );
  return (
    <nav aria-label="결과 좁히기" data-kw-filters data-div={filter.div ?? ""} data-due={filter.due ?? ""}
      className="mb-7 flex flex-wrap items-center gap-x-6 gap-y-2 max-sm:mb-5 max-sm:gap-x-4">
      <span className="flex flex-wrap items-center gap-x-3">
        <span className="t-k">구분</span>
        {chip(!filter.div, { ...filter, div: null }, "전체")}
        {DIVS.map((d) => chip(filter.div === d, { ...filter, div: d }, d))}
      </span>
      <span className="flex flex-wrap items-center gap-x-3">
        <span className="t-k">마감</span>
        {chip(!filter.due, { ...filter, due: null }, "전체")}
        {DUES.map(([n, label]) => chip(filter.due === n, { ...filter, due: n }, label))}
      </span>
    </nav>
  );
}

export const NO_FILTER: KeywordFilter = { div: null, due: null };
export const hasFilter = (f: KeywordFilter) => !!(f.div || f.due);
