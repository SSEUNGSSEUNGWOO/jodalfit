import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import {
  INDUSTRY_PER_PAGE,
  fetchIndustry,
  fetchIndustryCompanies,
  isIndustryCode,
} from "@/lib/industry";
import { maskBizrno } from "@/lib/utils";

interface Props {
  params: Promise<{ code: string; page: string }>;
}

// 업종별 집계 페이지 — "○○공사업 업체" 류 롱테일 검색의 착지점. 회사명 검색은 취업·신용
// 포털이 상단을 차지해 CTR 2%대지만, 집계 페이지는 조달핏만 가진 데이터로 1등을 노릴 수 있다.
// 원천 MV가 하루 한 번 갱신이라 ISR 하루. 빈 generateStaticParams가 있어야 ●(ISR)로 빌드된다.
export const revalidate = 86400;

export async function generateStaticParams() {
  return [];
}

function parseParams(code: string, page: string) {
  const pageNo = parseInt(page, 10);
  if (!isIndustryCode(code) || !Number.isFinite(pageNo) || pageNo < 1 || String(pageNo) !== page) {
    return null;
  }
  return { code, pageNo };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { code, page } = await params;
  const parsed = parseParams(code, page);
  const industry = parsed ? await fetchIndustry(parsed.code) : null;
  if (!parsed || !industry) {
    return { title: "업종별 기업 목록 | 조달핏", robots: { index: false } };
  }
  const count = industry.company_count.toLocaleString("ko-KR");
  const pageSuffix = parsed.pageNo > 1 ? ` ${parsed.pageNo}페이지` : "";
  return {
    title: `${industry.indstryty_nm} 등록 업체 ${count}곳${pageSuffix} | 조달핏`,
    description: `나라장터에 ${industry.indstryty_nm}(으)로 등록된 공공조달 참여 기업 ${count}개사 목록${pageSuffix}. 회사를 선택하면 수주 이력과 평균 투찰률, 맞춤 공고 추천을 볼 수 있습니다.`,
    alternates: { canonical: `/companies/industry/${parsed.code}/${parsed.pageNo}` },
  };
}

function PageLink({
  code,
  page,
  label,
  current,
}: {
  code: string;
  page: number;
  label: string;
  current?: boolean;
}) {
  if (current) {
    return (
      <span className="inline-flex h-9 min-w-9 items-center justify-center px-2 rounded-[3px] bg-gc-ink text-gc-paper text-[13.5px] font-bold tabular tabular-nums">
        {label}
      </span>
    );
  }
  return (
    <Link
      href={`/companies/industry/${code}/${page}`}
      className="inline-flex h-9 min-w-9 items-center justify-center px-2 rounded-[3px] border border-gc-rule bg-gc-sheet text-[13.5px] font-bold tabular tabular-nums text-gc-ink-2 hover:bg-gc-tint transition-colors"
    >
      {label}
    </Link>
  );
}

export default async function IndustryCompaniesPage({ params }: Props) {
  const { code, page } = await params;
  const parsed = parseParams(code, page);
  if (!parsed) notFound();

  const industry = await fetchIndustry(parsed.code);
  if (!industry) notFound();

  const rows = await fetchIndustryCompanies(parsed.code, parsed.pageNo);
  const totalPages = Math.max(1, Math.ceil(industry.company_count / INDUSTRY_PER_PAGE));
  if (rows.length === 0 && parsed.pageNo > 1) notFound();

  const p = parsed.pageNo;
  const neighbors = [p - 2, p - 1, p, p + 1, p + 2].filter(
    (x) => x >= 1 && x <= totalPages
  );

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-10 sm:pt-12 pb-16">
          <nav className="text-[12.5px] text-gc-ink-3" aria-label="브레드크럼">
            <Link href="/companies" className="hover:text-gc-ink font-semibold">
              공공조달 활동 기업
            </Link>
            <span className="mx-1.5">/</span>
            <Link href="/companies/industry" className="hover:text-gc-ink font-semibold">
              업종별
            </Link>
            <span className="mx-1.5">/</span>
            <span className="font-semibold text-gc-ink-2">{industry.indstryty_nm}</span>
          </nav>

          <div className="gc-double-rule mt-3 pt-4 pb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h1 className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
              {industry.indstryty_nm} 등록 업체
            </h1>
            <span className="text-[12.5px] text-gc-ink-3 tabular tabular-nums">
              {industry.company_count.toLocaleString("ko-KR")}개사 · {p.toLocaleString("ko-KR")} /{" "}
              {totalPages.toLocaleString("ko-KR")}페이지
            </span>
          </div>

          <p className="mt-3 max-w-[64ch] text-[14px] leading-[1.65] text-gc-ink-2 break-keep">
            나라장터에 {industry.indstryty_nm}(으)로 등록된 기업 중 조달핏이 수주 이력을
            분석한 회사입니다. 회사를 선택하면 낙찰 건수와 평균 투찰률, 지금 검토할 만한
            공고를 볼 수 있습니다.
          </p>

          <ol className="mt-6 border-t-2 border-gc-ink">
            {rows.map((r, i) => (
              <li key={r.bizrno_norm} className="border-b border-gc-rule">
                <Link
                  href={`/companies/${r.bizrno_norm}`}
                  className="grid items-baseline gap-x-4 px-1 py-3 grid-cols-[48px_minmax(0,1fr)] sm:grid-cols-[48px_minmax(0,1fr)_150px_90px] transition-colors hover:bg-gc-sheet"
                >
                  <span className="text-right pr-1 text-[13.5px] font-bold tabular tabular-nums text-gc-ink-3">
                    {((p - 1) * INDUSTRY_PER_PAGE + i + 1).toLocaleString("ko-KR")}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[15px] font-bold leading-[1.45] text-gc-ink break-keep">
                      {r.corp_nm}
                    </span>
                    <span className="mt-0.5 block text-[12px] tabular tabular-nums text-gc-ink-3">
                      {maskBizrno(r.bizrno)}
                    </span>
                  </span>
                  <span className="hidden sm:block text-[13px] text-gc-ink-2 break-keep self-start">
                    {r.rgn_nm ?? "—"}
                  </span>
                  <span className="hidden sm:block text-right text-[13px] text-gc-ink-3 self-start">
                    {r.corp_bsns_div_nm ?? "—"}
                  </span>
                </Link>
              </li>
            ))}
          </ol>

          <nav
            className="mt-6 flex flex-wrap items-center justify-center gap-1.5"
            aria-label="페이지 이동"
          >
            {p > 1 && <PageLink code={parsed.code} page={p - 1} label="← 이전" />}
            {neighbors[0] > 1 && (
              <>
                <PageLink code={parsed.code} page={1} label="1" />
                {neighbors[0] > 2 && <span className="px-1 text-gc-ink-3">…</span>}
              </>
            )}
            {neighbors.map((x) => (
              <PageLink key={x} code={parsed.code} page={x} label={String(x)} current={x === p} />
            ))}
            {neighbors[neighbors.length - 1] < totalPages && (
              <>
                {neighbors[neighbors.length - 1] < totalPages - 1 && (
                  <span className="px-1 text-gc-ink-3">…</span>
                )}
                <PageLink code={parsed.code} page={totalPages} label={String(totalPages)} />
              </>
            )}
            {p < totalPages && <PageLink code={parsed.code} page={p + 1} label="다음 →" />}
          </nav>
        </section>
      </main>
      <Footer className="mt-0" />
    </>
  );
}
