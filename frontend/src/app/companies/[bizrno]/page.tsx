import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { KeywordFallback } from "@/components/KeywordFallback";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  fetchCompanyByBizrno,
  fetchCompanyContracts,
  fetchCompanyProfile,
  summarizeContracts,
} from "@/lib/company";
import { getRecommendations } from "@/lib/api";
import { fetchGoldenTimeMap } from "@/lib/golden-time";
import { formatKRW, maskBizrno } from "@/lib/utils";

interface Props {
  params: Promise<{ bizrno: string }>;
}

// Cache for 1 hour, revalidate on demand
export const revalidate = 3600;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bizrno } = await params;
  const normalized = bizrno.replace(/\D/g, "");
  const company = await fetchCompanyByBizrno(normalized);
  if (!company) {
    return {
      title: "회사 정보 없음 | jodalfit",
      robots: { index: false },
    };
  }
  const title = `${company.corp_nm} 공공입찰 추천 | jodalfit`;
  const desc = `${company.corp_nm}의 과거 나라장터 수주 이력 분석과 적합한 신규 공공입찰 공고 TOP 5 추천. 매일 갱신.`;
  return {
    title,
    description: desc,
    alternates: { canonical: `/companies/${normalized}` },
    openGraph: {
      title,
      description: desc,
      type: "profile",
      locale: "ko_KR",
    },
    keywords: [
      company.corp_nm,
      `${company.corp_nm} 입찰`,
      `${company.corp_nm} 공고`,
      `${company.corp_nm} 수주`,
      "공공조달",
      "나라장터",
    ],
  };
}

export default async function CompanyPage({ params }: Props) {
  const { bizrno } = await params;
  const normalized = bizrno.replace(/\D/g, "");
  if (normalized.length !== 10) notFound();

  const company = await fetchCompanyByBizrno(normalized);
  if (!company) notFound();

  return (
    <>
      <Header />
      <main className="flex-1">
        <CompanyHero company={company} />
        <Suspense fallback={null}>
          <ProfileSection bizrno={company.bizrno} />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <RecommendationsSection company={company} />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <HistorySection bizrnoNorm={normalized} />
        </Suspense>
        <CTASection company={company} />
      </main>
      <Footer />
    </>
  );
}

// ───────────────────────────────────────────────────────────────
function CompanyHero({
  company,
}: {
  company: Awaited<ReturnType<typeof fetchCompanyByBizrno>> & object;
}) {
  return (
    <section className="border-b border-border bg-muted/30">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <div className="flex items-center gap-2 mb-3">
          <Badge variant="secondary" className="bg-primary/10 text-primary font-semibold">
            기업 분석
          </Badge>
          {company.is_restricted && (
            <Badge variant="destructive">부정당 제재</Badge>
          )}
        </div>
        <h1 className="text-[32px] sm:text-[44px] font-extrabold tracking-tight text-foreground leading-[1.1]">
          {company.corp_nm}
        </h1>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[14px] text-muted-foreground">
          <span className="font-medium tabular tabular-nums">
            사업자 {maskBizrno(company.bizrno)}
          </span>
          {company.rgn_nm && (
            <>
              <Dot />
              <span>{company.rgn_nm}</span>
            </>
          )}
          {company.corp_bsns_div_nm && (
            <>
              <Dot />
              <span>{company.corp_bsns_div_nm}</span>
            </>
          )}
          {company.ceo_nm && (
            <>
              <Dot />
              <span>대표 {company.ceo_nm}</span>
            </>
          )}
        </div>
        <p className="mt-6 max-w-[60ch] text-[15.5px] leading-[1.7] text-foreground/80">
          <span className="font-semibold text-foreground">{company.corp_nm}</span>의 과거
          나라장터 수주 이력을 분석해 가장 적합한 신규 공공입찰 공고를 추천해드려요. 매일 갱신되는 데이터로 분석합니다.
        </p>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────
async function ProfileSection({ bizrno }: { bizrno: string }) {
  const profile = await fetchCompanyProfile(bizrno);
  if (profile.industries.length === 0 && profile.products.length === 0) return null;

  return (
    <section className="border-b border-border bg-background">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        <h2 className="text-[18px] sm:text-[20px] font-bold text-foreground mb-4">
          이 회사가 하는 일
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {profile.industries.length > 0 && (
            <Card>
              <CardContent className="p-5">
                <div className="text-[12.5px] font-semibold text-muted-foreground mb-3">
                  등록업종 · {profile.industries.length}개
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {profile.industries.slice(0, 12).map((nm, i) => (
                    <Badge
                      key={`${nm}-${i}`}
                      variant={i === 0 ? "default" : "secondary"}
                      className={
                        i === 0
                          ? "bg-primary/15 text-primary border-primary/20 text-[12px]"
                          : "text-[12px]"
                      }
                    >
                      {nm}
                    </Badge>
                  ))}
                  {profile.industries.length > 12 && (
                    <span className="text-[12px] text-muted-foreground self-center">
                      +{profile.industries.length - 12}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
          {profile.products.length > 0 && (
            <Card>
              <CardContent className="p-5">
                <div className="text-[12.5px] font-semibold text-muted-foreground mb-3">
                  공급물품 · {profile.products.length}개
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {profile.products.slice(0, 12).map((nm, i) => (
                    <Badge
                      key={`${nm}-${i}`}
                      variant={i === 0 ? "default" : "secondary"}
                      className={
                        i === 0
                          ? "bg-primary/15 text-primary border-primary/20 text-[12px]"
                          : "text-[12px]"
                      }
                    >
                      {nm}
                    </Badge>
                  ))}
                  {profile.products.length > 12 && (
                    <span className="text-[12px] text-muted-foreground self-center">
                      +{profile.products.length - 12}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────
async function RecommendationsSection({
  company,
}: {
  company: Awaited<ReturnType<typeof fetchCompanyByBizrno>> & object;
}) {
  // 회사 벡터 없으면 폴백
  if (!company.has_embedding) {
    return (
      <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <div className="mb-5">
          <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
            추천 공고
          </h2>
          <p className="mt-1 text-[14px] text-muted-foreground">
            과거 수주 이력이 부족해 자동 매칭이 어려워요. 관심 영역을 직접 알려주시면 추천해드려요.
          </p>
        </div>
        <KeywordFallback />
      </section>
    );
  }

  // 추천 호출 — TOP 5 큰 카드 + 6~20 슬림 리스트
  const data = await getRecommendations({
    query: company.bizrno,
    mode: "company",
    limit: 20,
    with_explanation: true,
  });

  // 추천 결과 전체에 골든타임 정보 조회 (별도 섹션 + TOP 5 뱃지 모두에 사용)
  const goldenMap = await fetchGoldenTimeMap(
    data.results.map((b) => ({
      bid_ntce_no: b.bid_ntce_no,
      bid_ntce_date: b.bid_ntce_date,
      bid_clse_date: b.bid_clse_date,
    }))
  );

  // 골든타임(사전규격 공개중) 공고만 별도 섹션. spec_closing 우선, 그 안에서 점수순.
  const goldenRecs = data.results
    .filter((b) => {
      const g = goldenMap.get(b.bid_ntce_no);
      return g?.status === "spec_open" || g?.status === "spec_closing";
    })
    .sort((a, b) => {
      const ga = goldenMap.get(a.bid_ntce_no);
      const gb = goldenMap.get(b.bid_ntce_no);
      const aClosing = ga?.status === "spec_closing" ? 1 : 0;
      const bClosing = gb?.status === "spec_closing" ? 1 : 0;
      if (aClosing !== bClosing) return bClosing - aClosing;
      return b.score - a.score;
    })
    .slice(0, 3);
  const goldenSet = new Set(goldenRecs.map((b) => b.bid_ntce_no));
  const regularRecs = data.results.filter((b) => !goldenSet.has(b.bid_ntce_no));

  const TOP = 5;
  const top = regularRecs.slice(0, TOP);
  const slim = regularRecs.slice(TOP);

  return (
    <>
      {goldenRecs.length > 0 && (
        <section className="mx-auto max-w-[1140px] px-5 sm:px-8 pt-10 sm:pt-14">
          <div className="rounded-2xl border-2 border-amber-400 bg-amber-50/60 p-5 sm:p-7">
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-white text-[13px] font-extrabold">
                  ⚡
                </span>
                <h2 className="text-[20px] sm:text-[24px] font-extrabold text-amber-950 tracking-tight">
                  지금 의견 낼 수 있는 공고 {goldenRecs.length}건
                </h2>
              </div>
              <span className="text-[12px] text-amber-800 font-semibold">
                사전규격 단계 · 의견 등록으로 사양 반영 가능
              </span>
            </div>
            <p className="text-[13.5px] text-amber-900/80 mb-4 leading-relaxed">
              입찰공고가 뜨면 사양이 굳어져 변경이 어려워요. 지금이 사양에 의견을 낼 수 있는 마지막 타이밍이에요.
            </p>
            <div className="flex flex-col gap-3">
              {goldenRecs.map((bid) => (
                <BidCard
                  key={`golden-${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                  bid={bid}
                  golden={goldenMap.get(bid.bid_ntce_no)}
                />
              ))}
            </div>
          </div>
        </section>
      )}

    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
      <div className="flex items-baseline justify-between mb-5">
        <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
          {company.corp_nm}에 맞는 공고 {regularRecs.length}건
        </h2>
        <span className="text-[12.5px] text-muted-foreground font-medium">점수 순</span>
      </div>
      {data.results.length === 0 ? (
        <p className="text-[14.5px] text-muted-foreground">
          현재 매칭되는 신규 공고가 없어요. 나중에 다시 확인해보세요.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {top.map((bid, i) => (
              <BidCard
                key={`${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                bid={bid}
                rank={i + 1}
                golden={goldenMap.get(bid.bid_ntce_no)}
              />
            ))}
          </div>
          {slim.length > 0 && (
            <section className="mt-10">
              <div className="flex items-baseline justify-between mb-3 px-3">
                <h3 className="text-[15px] font-bold text-foreground">
                  관련 공고 {slim.length}개 더
                </h3>
                <span className="text-[11.5px] text-muted-foreground font-medium">
                  점수 / 마감 / 예산
                </span>
              </div>
              <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
                {slim.map((bid, i) => (
                  <SlimBidRow
                    key={`slim-${bid.bid_ntce_no}-${bid.bid_ntce_ord}`}
                    bid={bid}
                    rank={TOP + i + 1}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </section>
    </>
  );
}

// ───────────────────────────────────────────────────────────────
async function HistorySection({ bizrnoNorm }: { bizrnoNorm: string }) {
  const contracts = await fetchCompanyContracts(bizrnoNorm, 20);
  if (contracts.length === 0) return null;
  const summary = summarizeContracts(contracts);
  const totalAmt = contracts.reduce((s, r) => s + (r.cntrct_amt || 0), 0);

  return (
    <section className="border-t border-border bg-muted/20">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
          과거 수주 이력
        </h2>
        <p className="mt-1 text-[14px] text-muted-foreground">
          최근 {contracts.length}건의 계약 정보예요.
        </p>

        {/* 통계 카드 */}
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                누적 계약 (최근)
              </div>
              <div className="mt-2 text-[28px] font-extrabold tabular tabular-nums text-primary leading-none">
                {contracts.length}
                <span className="text-[14px] font-bold text-foreground/70 ml-1">건</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                누적 계약금액
              </div>
              <div className="mt-2 text-[28px] font-extrabold tabular tabular-nums text-primary leading-none">
                {formatKRW(totalAmt)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                주요 발주 기관
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {summary.top_institutions.slice(0, 3).map((s) => (
                  <Badge key={s} variant="secondary" className="text-[12px]">
                    {s.length > 14 ? s.slice(0, 14) + "..." : s}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 계약 리스트 */}
        <div className="mt-7 overflow-hidden rounded-xl border border-border bg-background">
          <table className="w-full text-[13.5px]">
            <thead className="bg-muted/60 text-[12px] font-semibold text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left">계약일</th>
                <th className="px-4 py-2.5 text-left">사업명</th>
                <th className="px-4 py-2.5 text-left">발주 기관</th>
                <th className="px-4 py-2.5 text-right">금액</th>
              </tr>
            </thead>
            <tbody>
              {contracts.slice(0, 10).map((c) => (
                <tr key={c.cntrct_no} className="border-t border-border">
                  <td className="px-4 py-2.5 tabular tabular-nums text-muted-foreground">
                    {c.cntrct_cncls_date ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-foreground">
                    {c.cntrct_nm || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {c.dmnd_instt_nm || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular tabular-nums font-bold text-foreground">
                    {formatKRW(c.cntrct_amt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────
function CTASection({
  company,
}: {
  company: Awaited<ReturnType<typeof fetchCompanyByBizrno>> & object;
}) {
  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-12 sm:py-16">
      <EmailCaptureForm />
    </section>
  );
}

function SectionSkeleton() {
  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10">
      <div className="h-7 w-48 bg-muted rounded animate-pulse" />
      <div className="mt-6 flex flex-col gap-3">
        <div className="h-32 w-full bg-muted/60 rounded-xl animate-pulse" />
        <div className="h-32 w-full bg-muted/60 rounded-xl animate-pulse" />
      </div>
    </section>
  );
}

function Dot() {
  return <span aria-hidden className="text-muted-foreground/50">·</span>;
}
