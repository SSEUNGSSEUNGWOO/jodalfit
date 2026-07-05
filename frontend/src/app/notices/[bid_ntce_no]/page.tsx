import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ExternalLink, FileText, MessageSquare, Award, FileSignature } from "lucide-react";
import { DDayBadge } from "@/components/DDayBadge";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Lifecycle } from "@/components/Lifecycle";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Suspense } from "react";
import { Sparkles } from "lucide-react";
import { fetchLifecycle, fetchSimilarNotices } from "@/lib/notice";
import { analyzeGoldenTime, isGoldenTime } from "@/lib/golden-time";
import { noticeJsonLd, serializeJsonLd } from "@/lib/jsonld";
import { cn, formatDateKR, formatKRW, maskBizrno } from "@/lib/utils";

interface Props {
  params: Promise<{ bid_ntce_no: string }>;
}

export const revalidate = 3600;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bid_ntce_no } = await params;
  const lifecycle = await fetchLifecycle(bid_ntce_no);
  if (!lifecycle) {
    return {
      title: "공고 정보 없음 | 조달핏",
      robots: { index: false },
    };
  }
  const { notice } = lifecycle;
  const title = `${notice.bid_ntce_nm} | 조달핏`;
  const desc = `${notice.dmnd_instt_nm ?? notice.ntce_instt_nm ?? ""} ${
    notice.bsns_div_nm ? `· ${notice.bsns_div_nm}` : ""
  } · 추정 ${formatKRW(notice.presmpt_prce)} · 마감 ${formatDateKR(notice.bid_clse_date)}. 발주계획부터 낙찰까지 전 과정 분석.`;
  return {
    title,
    description: desc,
    alternates: { canonical: `/notices/${bid_ntce_no}` },
    openGraph: {
      title: notice.bid_ntce_nm,
      description: desc,
      type: "article",
      locale: "ko_KR",
    },
    keywords: [
      notice.bid_ntce_nm,
      notice.bid_ntce_no,
      notice.dmnd_instt_nm ?? "",
      "공공입찰",
      "나라장터",
      "공공조달",
    ].filter(Boolean),
  };
}

export default async function NoticePage({ params }: Props) {
  const { bid_ntce_no } = await params;
  const lifecycle = await fetchLifecycle(bid_ntce_no);
  if (!lifecycle) notFound();

  const { notice, preSpecs, opinions, orderPlans, awards, contracts } = lifecycle;
  const gt = analyzeGoldenTime(lifecycle);
  const goldenActive = isGoldenTime(gt.status);
  const specPdfUrl = preSpecs[0]?.spec_doc_file_url_1;

  const jsonLd = noticeJsonLd({
    bidNtceNo: notice.bid_ntce_no,
    bidNtceNm: notice.bid_ntce_nm,
    description: `${notice.dmnd_instt_nm ?? notice.ntce_instt_nm ?? ""}${
      notice.bsns_div_nm ? ` · ${notice.bsns_div_nm}` : ""
    } · 추정 ${formatKRW(notice.presmpt_prce)} · 마감 ${formatDateKR(notice.bid_clse_date)}`,
    instituionName: notice.dmnd_instt_nm ?? notice.ntce_instt_nm,
    regionName: notice.prtcpt_psbl_rgn_nm,
    validFrom: notice.bid_ntce_date,
    validThrough: notice.bid_clse_date,
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />
      <Header />
      <main className="flex-1">
        {goldenActive && (
          <div className="bg-amber-500 text-white">
            <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13.5px] font-semibold">
              <span className="inline-flex items-center gap-1.5">
                <Sparkles className="h-4 w-4" strokeWidth={2.5} />
                <span className="font-extrabold tracking-tight">골든타임</span>
              </span>
              <span className="text-white/90">
                {gt.opinionDaysLeft !== null
                  ? gt.opinionDaysLeft === 0
                    ? "오늘이 의견 등록 마감일이에요"
                    : `의견 등록 마감 D-${gt.opinionDaysLeft}`
                  : "사전규격 공개중 — 의견 등록 가능"}
                {gt.opinionDeadline && (
                  <span className="ml-1.5 text-white/70 font-medium">
                    ({formatDateKR(gt.opinionDeadline)})
                  </span>
                )}
              </span>
              {gt.opinionCount > 0 && (
                <span className="text-white/80">
                  · 의견 {gt.opinionCount}건 등록됨
                </span>
              )}
              {specPdfUrl && (
                <a
                  href={specPdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto inline-flex items-center gap-1 rounded-md bg-white/15 hover:bg-white/25 px-2.5 py-1 text-[12.5px] font-bold transition-colors"
                >
                  사양서 PDF 보기
                </a>
              )}
            </div>
          </div>
        )}

        {/* Hero */}
        <section className="border-b border-border bg-muted/30">
          <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {notice.bsns_div_nm && (
                <Badge variant="secondary" className="bg-primary/10 text-primary font-semibold">
                  {notice.bsns_div_nm}
                </Badge>
              )}
              <span className="text-[12.5px] tabular tabular-nums text-muted-foreground font-medium">
                {notice.bid_ntce_no}
              </span>
              {notice.bid_clse_date && <DDayBadge date={notice.bid_clse_date} />}
            </div>

            <h1 className="text-[26px] sm:text-[36px] font-extrabold tracking-tight leading-[1.2] text-foreground max-w-[40ch]">
              {notice.bid_ntce_nm}
            </h1>

            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[14px] text-muted-foreground">
              <span className="font-semibold text-foreground/80">
                {notice.dmnd_instt_nm ?? notice.ntce_instt_nm ?? "—"}
              </span>
              {notice.bidprc_psbl_indstryty_nm && (
                <>
                  <Dot />
                  <span>참가가능 {notice.bidprc_psbl_indstryty_nm}</span>
                </>
              )}
              {notice.prtcpt_psbl_rgn_nm && (
                <>
                  <Dot />
                  <span>지역 {notice.prtcpt_psbl_rgn_nm}</span>
                </>
              )}
            </div>

            <div className="mt-7 grid gap-3 sm:grid-cols-3">
              <StatBlock
                label="추정가"
                value={formatKRW(notice.presmpt_prce)}
              />
              <StatBlock
                label="배정 예산"
                value={formatKRW(notice.asign_bdgt_amt)}
              />
              <StatBlock
                label="개찰일"
                value={
                  notice.openg_date ? formatDateKR(notice.openg_date) : "—"
                }
              />
            </div>

            {notice.bid_ntce_url && (
              <a
                href={notice.bid_ntce_url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "mt-6 inline-flex items-center gap-1.5 h-10 px-4 rounded-lg",
                  "bg-foreground text-background text-sm font-bold",
                  "hover:bg-foreground/90 transition-colors"
                )}
              >
                나라장터에서 보기 <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </section>

        {/* Lifecycle timeline */}
        <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
          <div className="mb-6">
            <h2 className="text-[22px] sm:text-[26px] font-extrabold text-foreground">
              공고 라이프사이클
            </h2>
            <p className="mt-1 text-[14px] text-muted-foreground">
              발주계획부터 계약체결까지 한 공고의 전 과정. 다른 입찰 사이트엔 없는 통합 정보예요.
            </p>
          </div>
          <Lifecycle data={lifecycle} />
        </section>

        {/* 발주 계획 */}
        {orderPlans.length > 0 && (
          <DetailSection
            title="발주 계획"
            subtitle="공고 등록 전 발주계획 단계에서 미리 공개된 정보"
            icon={<FileText className="h-4 w-4 text-primary" />}
          >
            <div className="flex flex-col gap-3">
              {orderPlans.map((p) => (
                <Card key={p.order_plan_unty_no}>
                  <CardContent className="p-5">
                    <h3 className="text-[16px] font-bold text-foreground">
                      {p.biz_nm || "—"}
                    </h3>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted-foreground">
                      <span>발주기관 {p.order_instt_nm ?? "—"}</span>
                      <Dot />
                      <span>
                        {p.order_year}.{p.order_mnth ?? "—"} 예정
                      </span>
                      {p.cntrct_mthd_nm && (
                        <>
                          <Dot />
                          <span>{p.cntrct_mthd_nm}</span>
                        </>
                      )}
                      {p.sum_order_amt && (
                        <>
                          <Dot />
                          <span className="font-semibold text-foreground/80 tabular tabular-nums">
                            {formatKRW(p.sum_order_amt)}
                          </span>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </DetailSection>
        )}

        {/* 사전 규격 */}
        {preSpecs.length > 0 && (
          <DetailSection
            title="사전 규격"
            subtitle="공고 게시 전 공개된 사양서. 사업 영역과 기술 요구사항을 미리 확인할 수 있어요."
            icon={<FileText className="h-4 w-4 text-primary" />}
          >
            <div className="flex flex-col gap-3">
              {preSpecs.map((s) => (
                <Card key={s.bf_spec_rgst_no}>
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div>
                        <h3 className="text-[16px] font-bold text-foreground">
                          {s.prdct_clsfc_no_nm || "—"}
                        </h3>
                        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[12.5px] text-muted-foreground">
                          <span>등록 {formatDateKR(s.rgst_dt?.split(" ")[0])}</span>
                          {s.opnin_rgst_clse_dt && (
                            <>
                              <Dot />
                              <span>
                                의견 마감 {formatDateKR(s.opnin_rgst_clse_dt.split(" ")[0])}
                              </span>
                            </>
                          )}
                          {s.sw_biz_obj_yn === "Y" && (
                            <>
                              <Dot />
                              <Badge
                                variant="secondary"
                                className="bg-primary/10 text-primary font-semibold"
                              >
                                SW사업
                              </Badge>
                            </>
                          )}
                        </div>
                      </div>
                      {s.asign_bdgt_amt && (
                        <div className="text-right">
                          <div className="text-[11.5px] font-semibold text-muted-foreground">
                            배정 예산
                          </div>
                          <div className="text-[16px] font-bold tabular tabular-nums">
                            {formatKRW(s.asign_bdgt_amt)}
                          </div>
                        </div>
                      )}
                    </div>
                    {s.spec_doc_file_url_1 && (
                      <a
                        href={s.spec_doc_file_url_1}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] font-bold text-primary hover:underline"
                      >
                        사양서 PDF <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </DetailSection>
        )}

        {/* 사전 규격 의견 */}
        {opinions.length > 0 && (
          <DetailSection
            title={`참여 업체 의견 ${opinions.length}건`}
            subtitle="이 공고의 사전규격에 대해 업체들이 낸 의견. '어떤 회사들이 관심을 가졌는지' 알 수 있어요."
            icon={<MessageSquare className="h-4 w-4 text-primary" />}
          >
            <div className="flex flex-col gap-3">
              {opinions.slice(0, 5).map((o) => (
                <Card key={`${o.bf_spec_rgst_no}-${o.opnin_no}`}>
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 text-[12.5px]">
                      <Badge variant="secondary" className="font-semibold">
                        {o.mkng_corp_nm || "—"}
                      </Badge>
                      {o.inpt_dt && (
                        <span className="text-muted-foreground">
                          {formatDateKR(o.inpt_dt.split(" ")[0])}
                        </span>
                      )}
                    </div>
                    {o.opnin_titl && (
                      <h3 className="mt-2 text-[15px] font-bold text-foreground">
                        {o.opnin_titl}
                      </h3>
                    )}
                    {o.opnin_cntnts && (
                      <p className="mt-1.5 text-[13.5px] leading-[1.65] text-foreground/80 line-clamp-3">
                        {o.opnin_cntnts}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </DetailSection>
        )}

        {/* 낙찰 결과 */}
        {awards.length > 0 && (
          <DetailSection
            title="개찰 결과"
            subtitle={`${awards.length}개 업체가 참가. 낙찰자와 투찰 정보예요.`}
            icon={<Award className="h-4 w-4 text-primary" />}
          >
            <div className="overflow-hidden rounded-xl border border-border bg-background">
              <table className="w-full text-[13.5px]">
                <thead className="bg-muted/60 text-[12px] font-semibold text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 text-left">순위</th>
                    <th className="px-4 py-2.5 text-left">업체명</th>
                    <th className="px-4 py-2.5 text-left">대표</th>
                    <th className="px-4 py-2.5 text-right">투찰금액</th>
                    <th className="px-4 py-2.5 text-right">낙찰률</th>
                  </tr>
                </thead>
                <tbody>
                  {awards.slice(0, 10).map((a) => (
                    <tr
                      key={`${a.bid_ntce_no}-${a.openg_rank}`}
                      className={cn(
                        "border-t border-border",
                        a.is_winner && "bg-primary/5"
                      )}
                    >
                      <td className="px-4 py-2.5 tabular tabular-nums font-bold">
                        {a.is_winner && (
                          <Badge className="bg-primary text-primary-foreground mr-1.5">
                            낙찰
                          </Badge>
                        )}
                        {a.openg_rank}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-foreground">
                        {a.corp_nm || "—"}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground">
                        {a.corp_ceo_nm || "—"}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular tabular-nums font-bold">
                        {formatKRW(a.bid_amt)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular tabular-nums text-muted-foreground">
                        {a.bid_rate ? `${a.bid_rate.toFixed(2)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DetailSection>
        )}

        {/* 계약 */}
        {contracts.length > 0 && (
          <DetailSection
            title="계약 체결"
            subtitle="이 공고의 최종 계약 정보예요."
            icon={<FileSignature className="h-4 w-4 text-primary" />}
          >
            <div className="flex flex-col gap-3">
              {contracts.map((c) => (
                <Card key={c.cntrct_no}>
                  <CardContent className="p-5">
                    <h3 className="text-[15.5px] font-bold text-foreground">
                      {c.cntrct_nm ?? notice.bid_ntce_nm}
                    </h3>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted-foreground">
                      <span className="font-semibold text-foreground/80">
                        {c.rprsnt_corp_nm}
                      </span>
                      {c.rprsnt_corp_bizrno && (
                        <span className="tabular tabular-nums">
                          {maskBizrno(c.rprsnt_corp_bizrno)}
                        </span>
                      )}
                      <Dot />
                      <span>
                        체결일 {formatDateKR(c.cntrct_cncls_date)}
                      </span>
                      <Dot />
                      <span className="font-bold tabular tabular-nums text-foreground/90">
                        {formatKRW(c.cntrct_amt)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </DetailSection>
        )}

        <Suspense fallback={null}>
          <SimilarSection bidNtceNo={lifecycle.notice.bid_ntce_no} />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}

async function SimilarSection({ bidNtceNo }: { bidNtceNo: string }) {
  const similar = await fetchSimilarNotices(bidNtceNo, 10);
  if (similar.length === 0) return null;

  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14 border-t border-border">
      <div className="mb-6">
        <h2 className="text-[20px] sm:text-[24px] font-extrabold tracking-tight text-foreground">
          비슷한 공고
        </h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          이 공고와 의미가 가까운 진행 중 공고 {similar.length}건이에요. 마감일이 지난 공고는 자동 제외.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {similar.map((s) => {
          const sim = Math.round(s.similarity * 100);
          return (
            <a
              key={s.bid_ntce_no}
              href={`/notices/${s.bid_ntce_no}`}
              className="block rounded-lg border border-border bg-card p-4 hover:border-primary/40 hover:shadow-sm transition-all"
            >
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-[15px] font-bold text-foreground leading-snug line-clamp-2">
                  {s.bid_ntce_nm}
                </div>
                <span className="shrink-0 text-[11px] font-bold text-primary tabular-nums">
                  유사도 {sim}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted-foreground">
                {s.bsns_div_nm && (
                  <Badge variant="secondary" className="text-[11px]">
                    {s.bsns_div_nm}
                  </Badge>
                )}
                <span className="truncate">
                  {s.dmnd_instt_nm || s.ntce_instt_nm || "—"}
                </span>
                {s.bid_clse_date && (
                  <>
                    <Dot />
                    <span>마감 {formatDateKR(s.bid_clse_date)}</span>
                  </>
                )}
                {s.presmpt_prce != null && (
                  <>
                    <Dot />
                    <span>추정 {formatKRW(s.presmpt_prce)}</span>
                  </>
                )}
              </div>
            </a>
          );
        })}
      </div>
    </section>
  );
}

function StatBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3">
      <div className="text-[12px] font-semibold text-muted-foreground">{label}</div>
      <div className="mt-1 text-[20px] font-extrabold tabular tabular-nums text-foreground">
        {value}
      </div>
    </div>
  );
}

function DetailSection({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-8 sm:py-10 border-t border-border">
      <div className="mb-5">
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-[20px] sm:text-[22px] font-extrabold text-foreground">
            {title}
          </h2>
        </div>
        {subtitle && (
          <p className="mt-1 text-[14px] text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {children}
    </section>
  );
}

function Dot() {
  return <span aria-hidden className="text-muted-foreground/50">·</span>;
}
