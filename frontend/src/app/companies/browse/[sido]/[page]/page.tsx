import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import {
  BROWSE_PER_PAGE,
  BROWSE_SIDO_LIST,
  fetchCompaniesBrowsePage,
} from "@/lib/company";
import { maskBizrno } from "@/lib/utils";

interface Props {
  params: Promise<{ sido: string; page: string }>;
}

// 사이트맵에만 있고 내부 링크로 닿지 않던 6만 회사 페이지의 크롤 경로.
// 데이터가 매일 갱신이라 ISR 하루. 빈 generateStaticParams가 있어야 ●(ISR)로 빌드된다.
export const revalidate = 86400;

export async function generateStaticParams() {
  return [];
}

function parseParams(sido: string, page: string) {
  const decoded = decodeURIComponent(sido);
  const validSido =
    decoded === "all" || (BROWSE_SIDO_LIST as readonly string[]).includes(decoded);
  const pageNo = parseInt(page, 10);
  if (!validSido || !Number.isFinite(pageNo) || pageNo < 1 || String(pageNo) !== page) {
    return null;
  }
  return { sido: decoded, pageNo };
}

const sidoLabel = (s: string) => (s === "all" ? "전체" : s);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { sido, page } = await params;
  const parsed = parseParams(sido, page);
  if (!parsed) return { title: "기업 목록 | 조달핏", robots: { index: false } };
  return {
    title: `공공조달 기업 목록 — ${sidoLabel(parsed.sido)} ${parsed.pageNo}페이지 | 조달핏`,
    description: `나라장터 공공조달에 참여한 ${sidoLabel(parsed.sido)} 기업 목록 ${parsed.pageNo}페이지. 회사를 선택하면 수주 이력과 맞춤 공고 추천을 볼 수 있습니다.`,
    alternates: { canonical: `/companies/browse/${encodeURIComponent(parsed.sido)}/${parsed.pageNo}` },
  };
}

function PageLink({
  sido,
  page,
  label,
  current,
}: {
  sido: string;
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
      href={`/companies/browse/${encodeURIComponent(sido)}/${page}`}
      className="inline-flex h-9 min-w-9 items-center justify-center px-2 rounded-[3px] border border-gc-rule bg-gc-sheet text-[13.5px] font-bold tabular tabular-nums text-gc-ink-2 hover:bg-gc-tint transition-colors"
    >
      {label}
    </Link>
  );
}

export default async function CompaniesBrowsePage({ params }: Props) {
  const { sido, page } = await params;
  const parsed = parseParams(sido, page);
  if (!parsed) notFound();

  const { rows, totalCount } = await fetchCompaniesBrowsePage(
    parsed.sido,
    parsed.pageNo
  );
  const totalPages = Math.max(1, Math.ceil(totalCount / BROWSE_PER_PAGE));
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
            <span className="font-semibold text-gc-ink-2">{sidoLabel(parsed.sido)}</span>
          </nav>

          <div className="gc-double-rule mt-3 pt-4 pb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h1 className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
              기업 목록 — {sidoLabel(parsed.sido)}
            </h1>
            <span className="text-[12.5px] text-gc-ink-3 tabular tabular-nums">
              {totalCount.toLocaleString("ko-KR")}개사 · {p.toLocaleString("ko-KR")} /{" "}
              {totalPages.toLocaleString("ko-KR")}페이지
            </span>
          </div>

          {/* 지역 캡슐 */}
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {["all", ...BROWSE_SIDO_LIST].map((s) => (
              <li key={s}>
                <Link
                  href={`/companies/browse/${encodeURIComponent(s)}/1`}
                  className={
                    s === parsed.sido
                      ? "inline-flex h-7 items-center rounded-full bg-gc-ink px-3 text-[12px] font-bold text-gc-paper"
                      : "inline-flex h-7 items-center rounded-full border border-gc-rule bg-gc-sheet px-3 text-[12px] font-semibold text-gc-ink-2 hover:bg-gc-tint transition-colors"
                  }
                >
                  {sidoLabel(s)}
                </Link>
              </li>
            ))}
          </ul>

          <ol className="mt-6 border-t-2 border-gc-ink">
            {rows.map((r, i) => (
              <li key={r.bizrno_norm} className="border-b border-gc-rule">
                <Link
                  href={`/companies/${r.bizrno_norm}`}
                  className="grid items-baseline gap-x-4 px-1 py-3 grid-cols-[48px_minmax(0,1fr)] sm:grid-cols-[48px_minmax(0,1fr)_150px_90px] transition-colors hover:bg-gc-sheet"
                >
                  <span className="text-right pr-1 text-[13.5px] font-bold tabular tabular-nums text-gc-ink-3">
                    {((p - 1) * BROWSE_PER_PAGE + i + 1).toLocaleString("ko-KR")}
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
            {p > 1 && <PageLink sido={parsed.sido} page={p - 1} label="← 이전" />}
            {neighbors[0] > 1 && (
              <>
                <PageLink sido={parsed.sido} page={1} label="1" />
                {neighbors[0] > 2 && <span className="px-1 text-gc-ink-3">…</span>}
              </>
            )}
            {neighbors.map((x) => (
              <PageLink key={x} sido={parsed.sido} page={x} label={String(x)} current={x === p} />
            ))}
            {neighbors[neighbors.length - 1] < totalPages && (
              <>
                {neighbors[neighbors.length - 1] < totalPages - 1 && (
                  <span className="px-1 text-gc-ink-3">…</span>
                )}
                <PageLink sido={parsed.sido} page={totalPages} label={String(totalPages)} />
              </>
            )}
            {p < totalPages && <PageLink sido={parsed.sido} page={p + 1} label="다음 →" />}
          </nav>
        </section>
      </main>
      <Footer className="mt-0" />
    </>
  );
}
