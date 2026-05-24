import type { Metadata } from "next";
import Link from "next/link";
import { MapPin, Briefcase, ArrowUpRight } from "lucide-react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { Card, CardContent } from "@/components/ui/card";
import { fetchBrowseCompanies } from "@/lib/company";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "공공조달 활동 기업 둘러보기 | jodalfit",
  description:
    "나라장터 수주 이력이 분석된 기업들. 각 회사의 활동 영역과 적합한 공공입찰 공고를 한눈에 확인하세요.",
  alternates: { canonical: "/companies" },
};

export default async function CompaniesIndexPage() {
  const companies = await fetchBrowseCompanies(30);

  return (
    <>
      <Header />
      <main className="flex-1">
        <section className="border-b border-border bg-muted/30">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
            <h1 className="text-[28px] sm:text-[36px] font-extrabold tracking-tight text-foreground">
              공공조달 활동 기업
            </h1>
            <p className="mt-3 max-w-[60ch] text-[15.5px] leading-[1.65] text-muted-foreground">
              나라장터 수주 이력이 분석된 기업 {companies.length}곳. 회사를 클릭하면
              해당 회사에 맞는 추천 공고와 과거 수주 분석을 볼 수 있어요.
            </p>
            <div className="mt-6 max-w-[520px]">
              <SearchForm />
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
                  <Card className="h-full transition-shadow hover:shadow-md">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between gap-2">
                        <h2 className="text-[16px] font-bold text-foreground group-hover:text-primary transition-colors">
                          {c.corp_nm}
                        </h2>
                        <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                      </div>
                      <div className="mt-3 flex flex-col gap-1 text-[12.5px] text-muted-foreground">
                        {c.rgn_nm && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" aria-hidden /> {c.rgn_nm}
                          </span>
                        )}
                        {c.corp_bsns_div_nm && (
                          <span className="flex items-center gap-1">
                            <Briefcase className="h-3 w-3" aria-hidden />{" "}
                            {c.corp_bsns_div_nm}
                          </span>
                        )}
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
