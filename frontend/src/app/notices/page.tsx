import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight, Calendar, MapPin, Building2, Gavel } from "lucide-react";
import { DDayBadge } from "@/components/DDayBadge";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fetchBrowseNotices } from "@/lib/notice";
import { cn, formatDateKR, formatKRW } from "@/lib/utils";

interface Props {
  searchParams: Promise<{ bsns_div?: string }>;
}

export const revalidate = 1800;

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

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <div className="flex flex-wrap gap-1.5">
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
              <span className="text-[12.5px] text-muted-foreground font-medium ml-auto">
                {notices.length}건 · 마감 임박 순
              </span>
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
                <Link
                  key={n.bid_ntce_no}
                  href={`/notices/${n.bid_ntce_no}`}
                  className="group"
                >
                  <Card className="h-full transition-shadow hover:shadow-md gap-0 py-0">
                    <CardContent className="p-5">
                      {/* Top row: badges */}
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {n.bsns_div_nm && (
                          <Badge
                            variant="secondary"
                            className="bg-primary/10 text-primary font-semibold"
                          >
                            {n.bsns_div_nm}
                          </Badge>
                        )}
                        {n.cntrct_cncls_mthd_nm && (
                          <Badge variant="secondary" className="font-medium">
                            {n.cntrct_cncls_mthd_nm}
                          </Badge>
                        )}
                        {n.rgn_lmt_yn === "Y" && (
                          <Badge variant="outline" className="text-[11px] font-semibold">
                            지역제한
                          </Badge>
                        )}
                        {n.bid_clse_date && (
                          <span className="ml-auto">
                            <DDayBadge date={n.bid_clse_date} />
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="mt-3 text-[16.5px] font-bold leading-[1.4] text-foreground group-hover:text-primary transition-colors line-clamp-2">
                        {n.bid_ntce_nm}
                      </h3>

                      {/* Institution */}
                      <div className="mt-2.5 flex items-center gap-1.5 text-[13px] text-foreground/80">
                        <Building2 className="h-3 w-3 text-muted-foreground" aria-hidden />
                        <span className="font-medium line-clamp-1">
                          {n.dmnd_instt_nm ?? n.ntce_instt_nm ?? "—"}
                        </span>
                      </div>

                      {/* Meta rows */}
                      <div className="mt-3 grid grid-cols-2 gap-y-1.5 gap-x-3 text-[12px]">
                        {n.bidprc_psbl_indstryty_nm && (
                          <MetaRow icon={<Gavel className="h-3 w-3" />} label="자격">
                            <span className="line-clamp-1">
                              {n.bidprc_psbl_indstryty_nm}
                            </span>
                          </MetaRow>
                        )}
                        {n.prtcpt_psbl_rgn_nm && (
                          <MetaRow icon={<MapPin className="h-3 w-3" />} label="지역">
                            <span className="line-clamp-1">{n.prtcpt_psbl_rgn_nm}</span>
                          </MetaRow>
                        )}
                        {n.bid_ntce_date && (
                          <MetaRow icon={<Calendar className="h-3 w-3" />} label="공고일">
                            {formatDateKR(n.bid_ntce_date)}
                          </MetaRow>
                        )}
                        {n.openg_date && (
                          <MetaRow icon={<Calendar className="h-3 w-3" />} label="개찰">
                            {formatDateKR(n.openg_date)}
                          </MetaRow>
                        )}
                      </div>

                      {/* Bottom: price + CTA */}
                      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                        <div>
                          <div className="text-[11px] font-semibold text-muted-foreground">
                            추정가
                          </div>
                          <div className="text-[16px] font-extrabold tabular tabular-nums text-foreground">
                            {formatKRW(n.presmpt_prce)}
                          </div>
                        </div>
                        <span className="inline-flex items-center gap-1 text-[12px] font-bold text-muted-foreground group-hover:text-primary transition-colors">
                          라이프사이클 <ArrowUpRight className="h-3.5 w-3.5" />
                        </span>
                      </div>

                      <div className="mt-2 text-[10.5px] tabular tabular-nums text-muted-foreground/70">
                        {n.bid_ntce_no}
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

function MetaRow({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-1.5 text-muted-foreground min-w-0">
      <span className="text-muted-foreground/70 shrink-0">{icon}</span>
      <span className="text-[11px] font-semibold uppercase tracking-[0.06em] shrink-0">
        {label}
      </span>
      <span className="text-foreground/80 truncate">{children}</span>
    </div>
  );
}
