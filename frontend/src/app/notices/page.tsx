import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Pagination } from "@/components/Pagination";
import { BoardSearch } from "@/components/board/BoardSearch";
import { SlimNoticeRow } from "@/components/SlimNoticeRow";
import {
  fetchBrowsePage,
  CATEGORY_LABELS,
  type NoticeCategory,
  type NoticeFilters,
} from "@/lib/notice";
import { cn } from "@/lib/utils";

interface Props {
  searchParams: Promise<{
    bsns_div?: string;
    dday?: string;
    price?: string;
    rgn?: string;
    cat?: string;
    sort?: string;
    page?: string;
  }>;
}

const CATEGORY_VALUES: NoticeCategory[] = [
  "it",
  "medical",
  "construction",
  "environment",
  "education",
  "consulting",
  "other",
];

function isCategory(v: string | undefined): v is NoticeCategory {
  return !!v && (CATEGORY_VALUES as string[]).includes(v);
}

export const revalidate = 1800;

const PAGE_SIZE = 100;

const BSNS_TABS = [
  { label: "전체", value: undefined },
  { label: "용역", value: "용역" },
  { label: "물품", value: "물품" },
  { label: "공사", value: "공사" },
  { label: "외자", value: "외자" },
];

const DDAY_OPTIONS: { label: string; value: NoticeFilters["dday"] | undefined }[] = [
  { label: "전체 마감", value: undefined },
  { label: "D-7 이내", value: 7 },
  { label: "D-14 이내", value: 14 },
  { label: "D-30 이내", value: 30 },
];

const PRICE_OPTIONS: { label: string; value: NoticeFilters["priceBucket"] | undefined }[] = [
  { label: "전체 예산", value: undefined },
  { label: "1억 미만", value: "lt1" },
  { label: "1억~10억", value: "1to10" },
  { label: "10억~50억", value: "10to50" },
  { label: "50억 이상", value: "gt50" },
];

const REGIONS = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
];

const SORT_OPTIONS: { label: string; value: NoticeFilters["sort"] }[] = [
  { label: "공고일 신규순", value: "ntce_desc" },
  { label: "마감 임박순", value: "close" },
  { label: "추정가 높은순", value: "price_desc" },
];

function parseFilters(s: Awaited<Props["searchParams"]>): NoticeFilters {
  const f: NoticeFilters = {};
  if (s.bsns_div) f.bsnsDiv = s.bsns_div;
  if (s.dday === "7" || s.dday === "14" || s.dday === "30") {
    f.dday = parseInt(s.dday, 10) as 7 | 14 | 30;
  }
  if (s.price === "lt1" || s.price === "1to10" || s.price === "10to50" || s.price === "gt50") {
    f.priceBucket = s.price;
  }
  if (s.rgn) f.rgn = s.rgn;
  if (isCategory(s.cat)) f.category = s.cat;
  if (s.sort === "price_desc" || s.sort === "ntce_desc" || s.sort === "close") {
    f.sort = s.sort;
  }
  return f;
}

function urlOf(filters: NoticeFilters, page?: number, replace?: Partial<NoticeFilters & { page?: number | null }>): string {
  const merged = { ...filters, ...replace } as NoticeFilters & { page?: number | null };
  const params = new URLSearchParams();
  if (merged.bsnsDiv) params.set("bsns_div", merged.bsnsDiv);
  if (merged.dday) params.set("dday", String(merged.dday));
  if (merged.priceBucket) params.set("price", merged.priceBucket);
  if (merged.rgn) params.set("rgn", merged.rgn);
  if (merged.category) params.set("cat", merged.category);
  if (merged.sort && merged.sort !== "ntce_desc") params.set("sort", merged.sort);
  const p = replace && "page" in replace ? replace.page : page;
  if (p && p > 1) params.set("page", String(p));
  const qs = params.toString();
  return qs ? `/notices?${qs}` : "/notices";
}

export async function generateMetadata({
  searchParams,
}: Props): Promise<Metadata> {
  const s = await searchParams;
  const pageNum = parseInt(s.page ?? "1", 10) || 1;
  const f = parseFilters(s);
  const titleBase = s.bsns_div
    ? `진행 중인 ${s.bsns_div} 입찰 공고`
    : "진행 중인 공공입찰 공고";
  const title = pageNum > 1 ? `${titleBase} ${pageNum}페이지 | 조달핏` : `${titleBase} | 조달핏`;
  const canonical = urlOf(f, pageNum);

  // 필터는 urlOf에서 병합되므로 조합 URL이 수만 개까지 늘어난다.
  // 단일 필터는 실제 검색어("서울 입찰공고")와 맞아떨어져 색인 가치가 있으니
  // 남기고, 조합·정렬·깊은 페이지만 뺀다. follow는 유지해야 공고 상세로
  // 가는 링크 흐름이 끊기지 않는다.
  const activeCount = [f.bsnsDiv, f.dday, f.priceBucket, f.rgn, f.category].filter(
    Boolean
  ).length;
  const isSorted = !!f.sort && f.sort !== "ntce_desc";
  // 단 "서울 용역 입찰공고"처럼 지역+업무구분 조합은 실제로 검색되는 말이라
  // 이 쌍만 예외로 색인을 남긴다. 아래 description도 이 두 값으로 만든다.
  const isRgnBsnsPair = activeCount === 2 && !!f.rgn && !!f.bsnsDiv;
  const noIndex = (activeCount >= 2 && !isRgnBsnsPair) || isSorted || pageNum > 3;

  // 필터가 걸린 페이지가 전부 같은 description을 쓰면 중복으로 취급된다.
  const scope = [f.rgn, f.bsnsDiv].filter(Boolean).join(" · ");
  const description = scope
    ? `${scope} 나라장터 입찰공고 중 마감 전인 공고를 모았습니다. 매일 갱신 · 나라장터 기반.`
    : "현재 마감 전인 나라장터 입찰공고를 마감·추정가·지역으로 필터링하여 둘러볼 수 있습니다.";

  return {
    title,
    description,
    alternates: { canonical },
    robots: noIndex ? { index: false, follow: true } : undefined,
  };
}

export default async function NoticesIndexPage({ searchParams }: Props) {
  const s = await searchParams;
  const filters = parseFilters(s);
  const currentPage = Math.max(1, parseInt(s.page ?? "1", 10) || 1);

  const { rows: notices, totalCount, categoryCounts } = await fetchBrowsePage(
    filters,
    currentPage,
    PAGE_SIZE
  );
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const startRank = (safePage - 1) * PAGE_SIZE;
  const sort = filters.sort ?? "ntce_desc";

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <section className="border-b border-border bg-muted/30">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-12">
            <h1 className="font-gc-serif font-black text-[28px] sm:text-[36px] tracking-[-0.02em] text-gc-ink">
              진행 중인 공공입찰
            </h1>
            <p className="mt-3 max-w-[60ch] text-[15.5px] leading-[1.65] text-muted-foreground">
              필터 조건에 맞는 공고 <span className="font-bold text-foreground">{totalCount.toLocaleString("ko-KR")}건</span>.
              공고를 클릭하면 발주계획부터 낙찰까지 전 과정을 한 페이지에서 확인할 수 있어요.
            </p>
            <div className="mt-6 max-w-[560px]">
              <BoardSearch />
            </div>
          </div>
        </section>

        {/* 필터 바 */}
        <section className="border-b border-border bg-background sticky top-16 z-30 backdrop-blur">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-4 space-y-2.5">
            <FilterRow label="분야">
              <ChipLink
                active={!filters.category}
                href={urlOf(filters, undefined, { category: undefined, page: null })}
              >
                전체
              </ChipLink>
              {CATEGORY_VALUES.map((cat) => (
                <ChipLink
                  key={cat}
                  active={filters.category === cat}
                  href={urlOf(filters, undefined, { category: cat, page: null })}
                >
                  {CATEGORY_LABELS[cat]}
                  <span className="ml-1 text-[10.5px] opacity-70 tabular-nums">
                    {categoryCounts[cat].toLocaleString("ko-KR")}
                  </span>
                </ChipLink>
              ))}
            </FilterRow>
            <FilterRow label="업무">
              {BSNS_TABS.map((t) => (
                <ChipLink
                  key={t.label}
                  active={t.value === filters.bsnsDiv}
                  href={urlOf(filters, undefined, { bsnsDiv: t.value, page: null })}
                >
                  {t.label}
                </ChipLink>
              ))}
            </FilterRow>
            <FilterRow label="마감">
              {DDAY_OPTIONS.map((t) => (
                <ChipLink
                  key={t.label}
                  active={t.value === filters.dday}
                  href={urlOf(filters, undefined, { dday: t.value, page: null })}
                >
                  {t.label}
                </ChipLink>
              ))}
            </FilterRow>
            <FilterRow label="예산">
              {PRICE_OPTIONS.map((t) => (
                <ChipLink
                  key={t.label}
                  active={t.value === filters.priceBucket}
                  href={urlOf(filters, undefined, { priceBucket: t.value, page: null })}
                >
                  {t.label}
                </ChipLink>
              ))}
            </FilterRow>
            <FilterRow label="지역">
              <ChipLink
                active={!filters.rgn}
                href={urlOf(filters, undefined, { rgn: undefined, page: null })}
              >
                전체
              </ChipLink>
              {REGIONS.map((r) => (
                <ChipLink
                  key={r}
                  active={filters.rgn === r}
                  href={urlOf(filters, undefined, { rgn: r, page: null })}
                >
                  {r}
                </ChipLink>
              ))}
            </FilterRow>
            <div className="flex flex-wrap items-center gap-2 pt-1.5 border-t border-border/60">
              <span className="text-[12px] font-bold text-muted-foreground w-[44px] shrink-0">정렬</span>
              {SORT_OPTIONS.map((o) => (
                <ChipLink
                  key={o.value}
                  active={sort === o.value}
                  href={urlOf(filters, undefined, { sort: o.value, page: null })}
                >
                  {o.label}
                </ChipLink>
              ))}
              <span className="text-[12.5px] text-muted-foreground font-medium ml-auto tabular-nums">
                {safePage}/{totalPages} 페이지
              </span>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
          <h2 className="sr-only">공고 목록</h2>
          {notices.length === 0 ? (
            <div className="rounded-xl bg-muted/40 border border-border p-8 text-center">
              <h3 className="text-[18px] font-bold text-foreground">
                해당 조건의 진행 중 공고가 없어요.
              </h3>
              <p className="mt-2 text-[14px] text-muted-foreground">
                필터를 조금 풀어보세요.
              </p>
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
                {notices.map((n, i) => (
                  <SlimNoticeRow
                    key={`${n.bid_ntce_no}-${safePage}-${i}`}
                    notice={n}
                    rank={startRank + i + 1}
                  />
                ))}
              </div>

              <Pagination
                current={safePage}
                totalPages={totalPages}
                hrefFor={(p) => urlOf(filters, p)}
              />
            </>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}

function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[12px] font-bold text-muted-foreground w-[44px] shrink-0">
        {label}
      </span>
      {children}
    </div>
  );
}

function ChipLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "px-2.5 py-1 rounded-full text-[12.5px] font-semibold transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "bg-background border border-border text-foreground hover:bg-muted"
      )}
    >
      {children}
    </Link>
  );
}
