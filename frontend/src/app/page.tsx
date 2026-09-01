import type { Metadata } from "next";
import Link from "next/link";
import { BoardSeal } from "@/components/board/BoardSeal";
import { BoardSearch } from "@/components/board/BoardSearch";
import { SubscribeBand } from "@/components/board/SubscribeBand";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { fetchBrowsePage, type NoticeSummary } from "@/lib/notice";
import { daysUntil, formatDateKR, formatKRW } from "@/lib/utils";

export const revalidate = 3600;

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default async function HomePage() {
  const board = await fetchBrowsePage({ sort: "ntce_desc" }, 1, 5).catch(
    () => null
  );

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <Hero activeCount={board?.totalCount ?? 0} />
        <TodayBoard rows={board?.rows ?? []} />
        <Features />
        <SubscribeBand />
      </main>
      <Footer className="mt-0" />
    </>
  );
}

/* ── 히어로 — 관보 1면의 제호와 판머리 ────────────────────── */

function issueLine() {
  const now = new Date();
  const y = now.getFullYear();
  const mmdd = `${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  const dateLabel = now.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
  return { issue: `제${y}-${mmdd}호`, dateLabel };
}

function Hero({ activeCount }: { activeCount: number }) {
  const { issue, dateLabel } = issueLine();
  return (
    <section className="bg-gc-band">
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-7 sm:pt-9 pb-12 sm:pb-16">
        {/* 제호 줄 — 매일 발행되는 판이라는 사실을 지면이 직접 말한다 */}
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-gc-band-ink/40 pb-3">
          <span className="font-gc-serif font-black text-[15px] tracking-[0.02em] text-gc-band-hi">
            조달핏
          </span>
          <span className="text-[12px] tabular tabular-nums text-gc-band-ink">
            {issue} · {dateLabel} · 매일 새벽 갱신
          </span>
        </div>

        <div className="mt-10 sm:mt-14 flex items-start justify-between gap-6">
          <div className="min-w-0 max-w-[720px]">
            <h1 className="font-gc-serif font-black text-[34px] sm:text-[54px] leading-[1.22] tracking-[-0.02em] text-gc-band-hi break-keep">
              오늘의 나라장터 공고를
              <br />
              우리 회사에 맞는 순서로.
            </h1>
            <p className="mt-5 text-[15.5px] sm:text-[17px] leading-[1.7] text-gc-band-ink max-w-[560px] break-keep">
              회사명만 입력하면 등록업종·공급물품·수주 이력을 살펴보고, 검토할 만한
              공고부터 보여드려요. 회원가입 없이 바로 확인할 수 있어요.
            </p>
          </div>
          <BoardSeal size={72} className="hidden sm:block shrink-0 mt-2" />
        </div>

        <div id="gc-search" className="mt-9 sm:mt-11 max-w-[640px] scroll-mt-24">
          <BoardSearch tone="band" autoFocus />
        </div>

        <p className="mt-8 text-[13px] text-gc-band-ink tabular tabular-nums">
          <span className="font-bold text-gc-band-hi">나라장터(G2B)</span> 진행 중
          공고{" "}
          <span className="font-bold text-gc-band-hi">
            {activeCount > 0 ? activeCount.toLocaleString("ko-KR") : "—"}건
          </span>{" "}
          · 매일 새벽 자동 갱신 · 공공 OpenAPI 기반
        </p>
      </div>
    </section>
  );
}

/* ── 오늘의 판 — 실제 공고가 곧 1면 기사 ─────────────────── */

function Dday({ date }: { date: string | null }) {
  const d = daysUntil(date);
  if (d === null) return <span className="text-gc-ink-3">—</span>;
  if (d < 0) return <span className="text-gc-ink-3">마감</span>;
  if (d > 60)
    return (
      <span className="text-gc-ink-3 tabular tabular-nums">
        ~{formatDateKR(date)}
      </span>
    );
  return (
    <span
      className={
        "tabular tabular-nums font-bold " +
        (d <= 2 ? "text-gc-injuk" : d <= 5 ? "text-gc-amber" : "text-gc-ink")
      }
    >
      {d === 0 ? "오늘" : `D-${d}`}
    </span>
  );
}

function TodayBoard({ rows }: { rows: NoticeSummary[] }) {
  if (rows.length === 0) return null;
  return (
    <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-14 sm:pt-16 pb-4">
      <div className="gc-double-rule pt-4 pb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-gc-serif font-black text-[21px] sm:text-[24px] tracking-[-0.02em] text-gc-ink">
          오늘의 판 — 방금 올라온 공고
        </h2>
        <span className="text-[12px] text-gc-ink-3">
          전체 공고 기준 최신 5건 · 매일 새벽 갱신
        </span>
      </div>

      <div
        aria-hidden
        className="hidden sm:grid grid-cols-[48px_minmax(0,1fr)_84px_120px] gap-x-4 px-1 mt-4 pb-2 border-b-2 border-gc-ink text-[11.5px] font-bold text-gc-ink-2"
      >
        <span className="text-right pr-1">순번</span>
        <span>공고</span>
        <span className="text-right">마감</span>
        <span className="text-right">추정가</span>
      </div>

      <ol>
        {rows.map((r, i) => (
          <li key={r.bid_ntce_no} className="border-b border-gc-rule">
            <Link
              href={`/notices/${r.bid_ntce_no}`}
              className="grid items-baseline gap-x-4 px-1 py-3.5 grid-cols-[40px_minmax(0,1fr)] sm:grid-cols-[48px_minmax(0,1fr)_84px_120px] transition-colors hover:bg-gc-sheet"
            >
              <span className="text-right pr-1 text-[15px] font-bold tabular tabular-nums text-gc-ink-2">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                <span className="block text-[15px] sm:text-[16px] font-bold leading-[1.45] text-gc-ink break-keep">
                  {r.bid_ntce_nm}
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px] text-gc-ink-3">
                  <span className="font-semibold text-gc-ink-2">
                    {r.dmnd_instt_nm || r.ntce_instt_nm || "—"}
                  </span>
                  {r.bsns_div_nm && (
                    <span className="border border-gc-rule rounded-[3px] px-1.5 py-px text-[11.5px] font-semibold text-gc-ink-2 bg-gc-sheet">
                      {r.bsns_div_nm}
                    </span>
                  )}
                  <span className="sm:hidden inline-flex items-center gap-2 tabular tabular-nums">
                    <Dday date={r.bid_clse_date} />
                    <span className="text-gc-ink-2 font-semibold">
                      {formatKRW(r.presmpt_prce ?? r.asign_bdgt_amt)}
                    </span>
                  </span>
                </span>
              </span>
              <span className="hidden sm:block text-right text-[14px] self-start">
                <Dday date={r.bid_clse_date} />
              </span>
              <span className="hidden sm:block text-right text-[14px] font-semibold tabular tabular-nums text-gc-ink self-start">
                {formatKRW(r.presmpt_prce ?? r.asign_bdgt_amt)}
              </span>
            </Link>
          </li>
        ))}
      </ol>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-gc-ink-3 break-keep">
          지금 이 판은 전체 공고 기준입니다. 회사를 조회하면{" "}
          <span className="font-bold text-gc-ink">
            우리 회사 기준 적합도 순
          </span>
          으로 다시 정렬되고, 행마다 추천 근거가 붙습니다.
        </p>
        <a
          href="#gc-search"
          className="inline-flex items-center h-10 px-4 bg-gc-band text-gc-band-hi text-[13.5px] font-bold rounded-[3px] hover:bg-gc-ink transition-colors whitespace-nowrap"
        >
          우리 회사 기준으로 정렬하기 ↑
        </a>
      </div>
    </section>
  );
}

/* ── 기능 행 ────────────────────────────────────────────── */

const FEATURES = [
  {
    href: "/recommendations",
    title: "회사 맞춤 추천",
    desc: "등록업종·공급물품·수주 이력으로 회사 벡터를 만들어 검토할 만한 공고를 우선순위로 정리해요. 행을 열면 추천 근거와 증거가 펼쳐지고, 검토 인장을 찍어 다시 찾을 수 있어요.",
    cta: "회사명으로 검색",
  },
  {
    href: "/notices",
    title: "공고 라이프사이클",
    desc: "발주계획 → 사전규격 → 공고 → 개찰 → 계약까지, 한 공고의 전 과정을 한 페이지에서 확인해요.",
    cta: "공고 둘러보기",
  },
  {
    href: "/insights",
    title: "주간 인사이트",
    desc: "분야별 검토할 만한 공고 픽과 시장 동향 리포트를 매주 발행해요.",
    cta: "인사이트 보기",
  },
];

function Features() {
  return (
    <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-12 pb-16 sm:pb-20">
      <h2 className="sr-only">조달핏이 도와드리는 것</h2>
      <div className="gc-double-rule">
        {FEATURES.map((f) => (
          <Link
            key={f.href}
            href={f.href}
            className="group grid sm:grid-cols-[200px_minmax(0,1fr)_auto] items-baseline gap-x-6 gap-y-1 py-5 border-b border-gc-rule transition-colors hover:bg-gc-sheet px-1"
          >
            <h3 className="font-gc-serif font-black text-[17px] text-gc-ink">
              {f.title}
            </h3>
            <p className="text-[13.5px] leading-[1.7] text-gc-ink-3 break-keep">
              {f.desc}
            </p>
            <span className="text-[13px] font-bold text-gc-band group-hover:underline underline-offset-4 whitespace-nowrap">
              {f.cta} →
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
