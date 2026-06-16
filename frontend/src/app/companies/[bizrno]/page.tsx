import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BidCard } from "@/components/BidCard";
import { SlimBidRow } from "@/components/SlimBidRow";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { EmbeddingSpaceViz } from "@/components/EmbeddingSpaceViz";
import { KeywordFallback } from "@/components/KeywordFallback";
import { OrderPlanSection } from "@/components/OrderPlanSection";
import { PreSpecSection } from "@/components/PreSpecSection";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  fetchCompanyAwards,
  fetchCompanyByBizrno,
  fetchCompanyContracts,
  fetchCompanyProfile,
  summarizeAwards,
  summarizeContracts,
} from "@/lib/company";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { getRecommendations } from "@/lib/api";
import { fetchCompanyDomainAnalysis } from "@/lib/company-profile";
import { companyOrganizationJsonLd, serializeJsonLd } from "@/lib/jsonld";
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

  // 데이터 가용성별 3단 후킹 (CTR 개선용)
  // 1) awards 있으면: 낙찰 건수 + 평균 투찰율
  // 2) contracts만 있으면: 누적 계약 건수
  // 3) 둘 다 없으면: 기본 톤
  const awards = await fetchCompanyAwards(normalized, 50);
  const awardSummary = summarizeAwards(awards);
  let desc: string;
  if (awardSummary.count >= 3 && awardSummary.avg_rate !== null) {
    desc = `${company.corp_nm} 공공입찰 분석 — 나라장터 낙찰 ${awardSummary.count}건, 평균 투찰율 ${awardSummary.avg_rate.toFixed(1)}%. 비슷한 신규 공고 TOP 5 매일 추천.`;
  } else if (company.contract_count >= 1) {
    desc = `${company.corp_nm}의 공공조달 수주 이력 ${company.contract_count}건 분석. 검토할 만한 신규 나라장터 공고 TOP 5를 매일 추천합니다.`;
  } else {
    desc = `${company.corp_nm}의 등록업종·공급물품 기반으로 적합한 신규 나라장터 공고 TOP 5를 추천합니다. 매일 갱신.`;
  }

  // 추천 벡터도 없고 수주 이력도 없는 깡통 페이지는 색인 제외
  // (구글 "발견됨-색인 생성되지 않음" 보류 해소)
  const isThin = !company.has_embedding && company.contract_count === 0;
  return {
    title,
    description: desc,
    alternates: { canonical: `/companies/${normalized}` },
    robots: isThin ? { index: false, follow: true } : undefined,
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

  const jsonLd = companyOrganizationJsonLd({
    bizrnoNorm: normalized,
    corpNm: company.corp_nm,
    ceoNm: company.ceo_nm,
    rgnNm: company.rgn_nm,
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />
      <Header />
      <main className="flex-1">
        <CompanyHero company={company} />
        <Suspense fallback={null}>
          <ProfileSection bizrno={company.bizrno} />
        </Suspense>
        <Suspense fallback={null}>
          <DomainAnalysisSection
            bizrnoNorm={normalized}
            companyName={company.corp_nm}
          />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <RecommendationsSection company={company} />
        </Suspense>
        <Suspense fallback={<SectionSkeleton />}>
          <HistorySection bizrnoNorm={normalized} />
        </Suspense>
        <Suspense fallback={null}>
          <AwardHistorySection bizrnoNorm={normalized} />
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
async function DomainAnalysisSection({
  bizrnoNorm,
  companyName,
}: {
  bizrnoNorm: string;
  companyName: string;
}) {
  const analysis = await fetchCompanyDomainAnalysis(bizrnoNorm);
  if (!analysis.isMultiDept || analysis.domains.length === 0) return null;

  const topDomains = analysis.domains.slice(0, 5);

  return (
    <section className="border-b border-border bg-amber-50/40">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10">
        <div className="rounded-2xl border border-amber-300 bg-white p-5 sm:p-7">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-amber-600" strokeWidth={2.5} />
            <h2 className="text-[18px] sm:text-[20px] font-extrabold text-amber-950 tracking-tight">
              jodalfit이 본 활동 영역
            </h2>
          </div>
          <p className="text-[14px] text-foreground/75 leading-relaxed">
            <span className="font-bold text-foreground">{companyName}</span>은 여러 영역에서 활동하는 회사로 보여요.
            회사 단위 추천은 영역들이 섞여 나올 수 있어요 — 특정 영역에 관심 있으시면 아래 키워드로 좁혀 검색하시면 더 정확해요.
          </p>

          {/* 영역 분포 막대 */}
          <div className="mt-5 space-y-2.5">
            {topDomains.map((d) => (
              <div key={d.domain}>
                <div className="flex items-center justify-between text-[12.5px] mb-1">
                  <span className="font-bold text-foreground">{d.label}</span>
                  <span className="text-muted-foreground tabular tabular-nums">
                    {Math.round(d.ratio * 100)}%
                    <span className="text-foreground/40 ml-1.5 font-medium">· {d.count}회 언급</span>
                  </span>
                </div>
                <div className="h-2 bg-amber-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full"
                    style={{ width: `${Math.max(d.ratio * 100, 2)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* 키워드 칩 */}
          <div className="mt-6 pt-5 border-t border-amber-200">
            <div className="text-[13px] font-bold text-foreground mb-2.5">
              어떤 영역의 공고를 보시겠어요?
            </div>
            <div className="flex flex-wrap gap-2">
              {topDomains.map((d) => (
                <Link
                  key={d.domain}
                  href={`/recommendations?company=${encodeURIComponent(companyName)}&keywords=${encodeURIComponent(d.suggestedKeyword)}`}
                  className="inline-flex items-center gap-1.5 rounded-full border border-amber-400 bg-white px-3.5 py-1.5 text-[13px] font-bold text-amber-900 hover:bg-amber-100 hover:border-amber-500 transition-colors"
                >
                  {d.label}
                  <span className="text-[11px] font-medium text-amber-600">
                    → &quot;{d.suggestedKeyword}&quot;
                  </span>
                </Link>
              ))}
            </div>
          </div>
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

  const TOP = 5;
  const top = data.results.slice(0, TOP);
  const slim = data.results.slice(TOP);

  return (
    <>
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
      <PreSpecSection results={data.pre_spec_results ?? []} />

      <div className="flex items-baseline justify-between mt-10 mb-5">
        <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
          {company.corp_nm}에 맞는 공고 {data.results.length}건
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

      <OrderPlanSection results={data.order_plan_results ?? []} />
    </section>

    {data.viz && (
      <EmbeddingSpaceViz viz={data.viz} companyName={company.corp_nm} />
    )}
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

// ───────────────────────────────────────────────────────────────
async function AwardHistorySection({ bizrnoNorm }: { bizrnoNorm: string }) {
  const awards = await fetchCompanyAwards(bizrnoNorm, 50);
  if (awards.length === 0) return null;
  const summary = summarizeAwards(awards);
  const fmtRate = (v: number | null) => (v == null ? "—" : `${v.toFixed(1)}%`);

  return (
    <section className="border-t border-border bg-background">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
        <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
          낙찰 패턴 회고
        </h2>
        <p className="mt-1 text-[14px] text-muted-foreground">
          최근 {awards.length}건의 낙찰가율 분포예요. 비슷한 공고 검토 시 참고하세요.
        </p>

        {/* 통계 카드 */}
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                평균 낙찰가율
              </div>
              <div className="mt-2 text-[28px] font-extrabold tabular tabular-nums text-primary leading-none">
                {fmtRate(summary.avg_rate)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                범위 (최저 ~ 최고)
              </div>
              <div className="mt-2 text-[18px] font-extrabold tabular tabular-nums text-foreground leading-none">
                {fmtRate(summary.min_rate)} ~ {fmtRate(summary.max_rate)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="text-[12.5px] font-semibold text-muted-foreground">
                낙찰 총액 (최근)
              </div>
              <div className="mt-2 text-[18px] font-extrabold tabular tabular-nums text-foreground leading-none">
                {formatKRW(summary.total_amt)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 낙찰 리스트 */}
        <div className="mt-7 overflow-hidden rounded-xl border border-border bg-background">
          <table className="w-full text-[13.5px]">
            <thead className="bg-muted/60 text-[12px] font-semibold text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left">공고명</th>
                <th className="px-4 py-2.5 text-left">발주 기관</th>
                <th className="px-4 py-2.5 text-right">낙찰가</th>
                <th className="px-4 py-2.5 text-right">투찰율</th>
              </tr>
            </thead>
            <tbody>
              {awards.slice(0, 10).map((a) => (
                <tr key={`${a.bid_ntce_no}-${a.bid_ntce_ord}`} className="border-t border-border">
                  <td className="px-4 py-2.5 font-medium text-foreground">
                    {a.bid_ntce_nm ? (
                      <Link
                        href={`/notices/${a.bid_ntce_no}`}
                        className="hover:text-primary transition-colors"
                      >
                        {a.bid_ntce_nm}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground tabular tabular-nums">{a.bid_ntce_no}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {a.dmnd_instt_nm || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular tabular-nums font-bold text-foreground">
                    {formatKRW(a.bid_amt)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular tabular-nums font-bold text-primary">
                    {fmtRate(a.bid_rate)}
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
