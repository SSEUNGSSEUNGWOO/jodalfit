import type { Metadata } from "next";
import Link from "next/link";
import {
  MapPin,
  Briefcase,
  ArrowUpRight,
  User,
  Globe,
  Calendar,
} from "lucide-react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { BoardSearch } from "@/components/board/BoardSearch";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fetchBrowseCompanies } from "@/lib/company";
import { formatDateKR, formatKRW, maskBizrno } from "@/lib/utils";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "공공조달 활동 기업 둘러보기 | 조달핏",
  description:
    "나라장터 수주 이력이 분석된 기업들. 각 회사의 활동 영역과 적합한 공공입찰 공고를 한눈에 확인하세요.",
  alternates: { canonical: "/companies" },
};

export default async function CompaniesIndexPage() {
  const companies = await fetchBrowseCompanies(30);

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <section className="border-b border-border bg-muted/30">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
            <h1 className="font-gc-serif font-black text-[28px] sm:text-[36px] tracking-[-0.02em] text-gc-ink">
              공공조달 활동 기업
            </h1>
            <p className="mt-3 max-w-[60ch] text-[15.5px] leading-[1.65] text-muted-foreground">
              나라장터 수주 이력이 분석된 기업 {companies.length}곳. 회사를 클릭하면
              해당 회사에 맞는 추천 공고와 과거 수주 분석을 볼 수 있어요.
            </p>
            <div className="mt-6 max-w-[560px]">
              <BoardSearch />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
          {companies.length === 0 ? (
            <p className="text-[14.5px] text-muted-foreground">
              아직 분석된 회사가 없어요. 잠시 후 다시 방문해주세요.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {companies.map((c) => (
                <Link
                  key={c.bizrno}
                  href={`/companies/${c.bizrno_norm}`}
                  className="group"
                >
                  <Card className="h-full transition-shadow hover:shadow-md gap-0 py-0">
                    <CardContent className="p-5">
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <h2 className="text-[16.5px] font-bold text-foreground group-hover:text-primary transition-colors line-clamp-2">
                            {c.corp_nm}
                          </h2>
                          <div className="mt-1 text-[11.5px] tabular tabular-nums text-muted-foreground">
                            {maskBizrno(c.bizrno)}
                          </div>
                        </div>
                        <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                      </div>

                      {/* Sector badges */}
                      {c.recent_sectors && c.recent_sectors.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {c.recent_sectors.map((s) => (
                            <Badge
                              key={s}
                              variant="secondary"
                              className="bg-primary/10 text-primary font-semibold text-[11px]"
                            >
                              {s}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* Meta */}
                      <div className="mt-3 flex flex-col gap-1.5 text-[12.5px] text-muted-foreground">
                        {c.ceo_nm && (
                          <Meta icon={<User className="h-3 w-3" />}>
                            대표 {c.ceo_nm}
                          </Meta>
                        )}
                        {c.rgn_nm && (
                          <Meta icon={<MapPin className="h-3 w-3" />}>
                            {c.rgn_nm}
                          </Meta>
                        )}
                        {c.corp_bsns_div_nm && (
                          <Meta icon={<Briefcase className="h-3 w-3" />}>
                            {c.corp_bsns_div_nm}
                          </Meta>
                        )}
                        {c.opng_dt && (
                          <Meta icon={<Calendar className="h-3 w-3" />}>
                            개업 {formatDateKR(c.opng_dt)}
                          </Meta>
                        )}
                        {c.hmpg_addr && (
                          <Meta icon={<Globe className="h-3 w-3" />}>
                            <span className="line-clamp-1">{c.hmpg_addr}</span>
                          </Meta>
                        )}
                      </div>

                      {/* Stats footer */}
                      {(c.contract_count ?? 0) > 0 && (
                        <div className="mt-4 pt-3 border-t border-border grid grid-cols-2 gap-3">
                          <div>
                            <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                              누적 수주
                            </div>
                            <div className="mt-0.5 text-[18px] font-extrabold tabular tabular-nums text-primary leading-none">
                              {c.contract_count}
                              <span className="text-[11px] ml-1 text-foreground/60">건</span>
                            </div>
                          </div>
                          {(c.recent_amount ?? 0) > 0 && (
                            <div>
                              <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                                누적 금액
                              </div>
                              <div className="mt-0.5 text-[18px] font-extrabold tabular tabular-nums text-foreground leading-none">
                                {formatKRW(c.recent_amount)}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
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

function Meta({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-muted-foreground/60 shrink-0">{icon}</span>
      <span className="text-foreground/80">{children}</span>
    </span>
  );
}
