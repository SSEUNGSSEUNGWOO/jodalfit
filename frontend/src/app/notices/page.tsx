import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { DDayBadge } from "@/components/DDayBadge";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fetchBrowseNotices } from "@/lib/notice";
import { cn, formatKRW } from "@/lib/utils";

interface Props {
  searchParams: Promise<{ bsns_div?: string }>;
}

export const revalidate = 1800; // 30분

export async function generateMetadata({
  searchParams,
}: Props): Promise<Metadata> {
  const { bsns_div } = await searchParams;
  const title = bsns_div
    ? `진행 중인 ${bsns_div} 입찰 공고 | jodalfit`
    : "진행 중인 공공입찰 공고 둘러보기 | jodalfit";
  return {
    title,
    description: bsns_div
      ? `현재 마감 전인 ${bsns_div} 부문 나라장터 입찰공고. 각 공고의 라이프사이클(발주계획→사전규격→낙찰) 분석 제공.`
      : "현재 마감 전인 나라장터 입찰공고 모음. 각 공고의 발주계획부터 낙찰까지 전 과정을 분석합니다.",
    alternates: { canonical: "/notices" },
  };
}

const TABS = [
  { label: "전체", value: undefined },
  { label: "용역", value: "용역" },
  { label: "물품", value: "물품" },
  { label: "공사", value: "공사" },
  { label: "외자", value: "외자" },
];

export default async function NoticesIndexPage({ searchParams }: Props) {
  const { bsns_div } = await searchParams;
  const notices = await fetchBrowseNotices(40, bsns_div);

  return (
    <>
      <Header />
      <main className="flex-1">
        <section className="border-b border-border bg-muted/30">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
            <h1 className="text-[28px] sm:text-[36px] font-extrabold tracking-tight text-foreground">
              진행 중인 공공입찰
            </h1>
            <p className="mt-3 max-w-[60ch] text-[15.5px] leading-[1.65] text-muted-foreground">
              현재 마감 전인 나라장터 입찰공고예요. 공고를 클릭하면 발주계획부터 낙찰까지
              전 과정을 한 페이지에서 확인할 수 있어요.
            </p>
            <div className="mt-6 max-w-[520px]">
              <SearchForm />
            </div>

            <div className="mt-6 flex flex-wrap gap-1.5">
              {TABS.map((t) => {
                const active = t.value === bsns_div;
                return (
                  <Link
                    key={t.label}
                    href={t.value ? `/notices?bsns_div=${t.value}` : "/notices"}
                    className={cn(
                      "px-3.5 py-1.5 rounded-full text-[13px] font-semibold transition-colors",
                      active
                        ? "bg-primary text-primary-foreground"
                        : "bg-background border border-border text-foreground hover:bg-muted"
                    )}
                  >
                    {t.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
          <h2 className="sr-only">공고 목록</h2>
          {notices.length === 0 ? (
            <p className="text-[14.5px] text-muted-foreground">
              해당 조건의 진행 중 공고가 없어요.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {notices.map((n) => (
                <Link key={n.bid_ntce_no} href={`/notices/${n.bid_ntce_no}`} className="group">
                  <Card className="h-full transition-shadow hover:shadow-md">
                    <CardContent className="p-5">
                      <div className="flex items-center gap-2 mb-2">
                        {n.bsns_div_nm && (
                          <Badge
                            variant="secondary"
                            className="bg-primary/10 text-primary font-semibold"
                          >
                            {n.bsns_div_nm}
                          </Badge>
                        )}
                        {n.bid_clse_date && <DDayBadge date={n.bid_clse_date} />}
                      </div>
                      <h3 className="text-[16px] font-bold leading-[1.4] text-foreground group-hover:text-primary transition-colors line-clamp-2">
                        {n.bid_ntce_nm}
                      </h3>
                      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-2 text-[12.5px]">
                        <span className="text-muted-foreground line-clamp-1">
                          {n.dmnd_instt_nm ?? "—"}
                        </span>
                        <span className="font-bold text-foreground/80 tabular tabular-nums">
                          {formatKRW(n.presmpt_prce)}
                        </span>
                      </div>
                      <div className="mt-3 flex items-center justify-end text-[12px] font-semibold text-muted-foreground group-hover:text-primary transition-colors">
                        라이프사이클 보기{" "}
                        <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
