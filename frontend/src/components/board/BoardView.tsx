"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BoardFilterBar, EMPTY_FILTERS, isFiltered, type BoardFilters } from "@/components/board/BoardFilterBar";
import { BoardRow, bidKey } from "@/components/board/BoardRow";
import { BoardSeal } from "@/components/board/BoardSeal";
import { BoardSearch } from "@/components/board/BoardSearch";
import { SubscribeBand } from "@/components/board/SubscribeBand";
import { emitNoticeEvent, getSessionId } from "@/lib/events";
import { MOCK_RESPONSE } from "@/lib/mock-data";
import { useShortlist } from "@/lib/shortlist";
import { cn, daysUntil, formatKRW, maskBizrno } from "@/lib/utils";
import type {
  BidRecommendation,
  OrderPlanRecommendation,
  PreSpecRecommendation,
  RecommendationResponse,
} from "@/types/recommendations";

const TOP_N = 5;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
/** 네트워크/서버 연결 실패 표식 — 식별 실패와 구분해 렌더 */
const NETWORK_ERROR = "__network__";

type Mode = "company" | "keywords";
type Algorithm = "v1" | "v2";

interface Props {
  query: string;
  mode: Mode;
  useMock: boolean;
  keywords?: string;
  algorithm?: Algorithm;
}

/** 개찰판 — 추천 결과 표면의 루트. 스트리밍 수신 + 조건 적용 + 판 렌더. */
export function BoardView({ query, mode, useMock, keywords, algorithm = "v2" }: Props) {
  const [data, setData] = useState<RecommendationResponse | null>(
    useMock ? MOCK_RESPONSE : null
  );
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<string>("");
  const [streamDone, setStreamDone] = useState<boolean>(useMock);
  const [openKeys, setOpenKeys] = useState<Set<string>>(() =>
    useMock && MOCK_RESPONSE.results[0]
      ? new Set([bidKey(MOCK_RESPONSE.results[0])])
      : new Set()
  );

  // 쿼리가 바뀌면 page.tsx가 키로 리마운트 — 상태 리셋은 초기값이 담당
  useEffect(() => {
    if (useMock) return;

    const controller = new AbortController();
    let cancelled = false;

    // 1회 시도 — 네트워크 실패·5xx는 throw해서 바깥 재시도 루프가 받는다
    const attempt = async () => {
      const res = await fetch(`${API_BASE}/recommendations/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          mode,
          keywords: keywords || null,
          algorithm,
          session_id: getSessionId(),
          limit: 20,
          candidate_pool: 200,
          explain_top: TOP_N,
          with_explanation: true,
        }),
        signal: controller.signal,
      });
      if (!res.ok) {
        // 5xx는 서버 기동 중일 수 있음 — 재시도 대상
        if (res.status >= 500) throw new Error(`HTTP ${res.status}`);
        const text = await res.text().catch(() => "");
        let detail = `HTTP ${res.status}`;
        try {
          const j = JSON.parse(text);
          detail = j.detail ?? j.error ?? detail;
        } catch {
          // 텍스트 응답이면 그대로
        }
        if (!cancelled) {
          setData({ company: null, results: [], error: detail });
          setStreamDone(true);
        }
        return;
      }
      if (!res.body) {
        if (!cancelled) setStreamDone(true);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const evt = JSON.parse(line);
            if (evt.type === "results") {
              const d = evt.data as RecommendationResponse;
              if (!cancelled) {
                setData(d);
                // 첫 행은 개봉된 채로 도착 — 판의 첫 인상이 곧 근거
                if (d.results?.[0]) setOpenKeys(new Set([bidKey(d.results[0])]));
              }
            } else if (evt.type === "explanation" && evt.scope === "primary") {
              const k = `${evt.bid_ntce_no}-${evt.bid_ntce_ord}`;
              if (!cancelled)
                setExplanations((prev) => ({ ...prev, [k]: evt.text as string }));
            } else if (evt.type === "summary") {
              if (!cancelled && evt.text) setSummary(evt.text as string);
            } else if (evt.type === "done") {
              if (!cancelled) setStreamDone(true);
            }
          } catch {
            // 끊긴 라인은 무시
          }
        }
      }
      if (!cancelled) setStreamDone(true);
    };

    // 백엔드 콜드 스타트 대비: 네트워크 실패는 3초 뒤 1회 자동 재시도.
    // 그래도 실패하면 "식별 실패"로 위장하지 않고 연결 오류로 정직하게 표시.
    (async () => {
      const MAX_ATTEMPTS = 2;
      for (let i = 0; i < MAX_ATTEMPTS; i++) {
        try {
          await attempt();
          return;
        } catch (e) {
          if ((e as Error).name === "AbortError" || cancelled) return;
          if (i < MAX_ATTEMPTS - 1) {
            await new Promise((r) => setTimeout(r, 3000));
            continue;
          }
          if (!cancelled) {
            setData({ company: null, results: [], error: NETWORK_ERROR });
            setStreamDone(true);
          }
        }
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [query, mode, useMock, keywords, algorithm]);

  if (!data) return <BoardLoading label={query} mode={mode} />;

  if (data.error === NETWORK_ERROR) {
    return <ConnectionErrorBoard query={query} />;
  }

  if (mode === "company" && (data.fallback === "keywords" || !data.company)) {
    return <FallbackBoard query={query} identified={!!data.company} message={data.error} />;
  }

  return (
    <ResultsBoard
      query={query}
      mode={mode}
      keywords={keywords}
      mock={useMock}
      data={data}
      explanations={explanations}
      summary={summary}
      streamDone={streamDone}
      openKeys={openKeys}
      setOpenKeys={setOpenKeys}
    />
  );
}

/* ── 결과 개찰판 ─────────────────────────────────────────── */

function ResultsBoard({
  query,
  mode,
  keywords,
  mock = false,
  data,
  explanations,
  summary,
  streamDone,
  openKeys,
  setOpenKeys,
}: {
  query: string;
  mode: Mode;
  keywords?: string;
  mock?: boolean;
  data: RecommendationResponse;
  explanations: Record<string, string>;
  summary: string;
  streamDone: boolean;
  openKeys: Set<string>;
  setOpenKeys: React.Dispatch<React.SetStateAction<Set<string>>>;
}) {
  const [filters, setFilters] = useState<BoardFilters>(EMPTY_FILTERS);
  const shortlist = useShortlist();
  const results = data.results;

  const divOptions = useMemo(
    () => [...new Set(results.map((r) => r.bsns_div_nm).filter(Boolean))] as string[],
    [results]
  );

  const visible = useMemo(
    () =>
      results
        .map((bid, i) => ({ bid, rank: i + 1 }))
        .filter(({ bid }) => {
          if (filters.savedOnly && !shortlist.has(bidKey(bid))) return false;
          if (filters.div && bid.bsns_div_nm !== filters.div) return false;
          if (filters.deadline !== undefined) {
            const d = daysUntil(bid.bid_clse_date);
            if (d === null || d < 0 || d > filters.deadline) return false;
          }
          if (filters.budget) {
            const p = bid.presmpt_prce;
            if (p == null) return false;
            const [min, max] = filters.budget;
            if (p < min || (max !== null && p >= max)) return false;
          }
          return true;
        }),
    [results, filters, shortlist]
  );

  const withExplanation = (b: BidRecommendation): BidRecommendation => {
    const k = bidKey(b);
    return explanations[k] ? { ...b, explanation: explanations[k] } : b;
  };

  const toggleOpen = (bid: BidRecommendation, rank: number) => {
    const k = bidKey(bid);
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(k)) {
        next.delete(k);
      } else {
        next.add(k);
        emitNoticeEvent({
          event_type: "click",
          bid_ntce_no: bid.bid_ntce_no,
          bid_ntce_ord: bid.bid_ntce_ord,
          target_bizrno: data.company?.bizrno ?? null,
          rank_position: rank,
          algorithm_version: data.algorithm ?? "v1",
          score: bid.score,
        });
      }
      return next;
    });
  };

  const toggleSave = (bid: BidRecommendation, rank: number) => {
    const k = bidKey(bid);
    if (!shortlist.has(k)) {
      emitNoticeEvent({
        event_type: "save",
        bid_ntce_no: bid.bid_ntce_no,
        bid_ntce_ord: bid.bid_ntce_ord,
        target_bizrno: data.company?.bizrno ?? null,
        rank_position: rank,
        algorithm_version: data.algorithm ?? "v1",
        score: bid.score,
      });
    }
    shortlist.toggle({
      k,
      bid_ntce_no: bid.bid_ntce_no,
      bid_ntce_ord: bid.bid_ntce_ord,
      bid_ntce_nm: bid.bid_ntce_nm,
      bid_clse_date: bid.bid_clse_date,
    });
  };

  const today = new Date().toLocaleDateString("ko-KR");

  return (
    <div className="world-gc flex-1">
      <BoardHead
        title={mode === "company" ? query : `“${query}”`}
        meta={
          mode === "company"
            ? [
                data.company?.bizrno ? maskBizrno(data.company.bizrno) : null,
                data.company?.rgn_nm ?? null,
                data.company?.corp_bsns_div_nm ?? null,
              ]
            : ["키워드 의미 매칭"]
        }
        criteria={
          mode === "company"
            ? keywords
              ? `등록업종·공급물품·수주 이력 + “${keywords}” 기준`
              : "등록업종·공급물품·수주 이력 기준"
            : "AI 의미 유사도 기준 — 같은 단어가 없어도 가까운 공고를 찾습니다"
        }
        count={results.length}
        date={today}
        searchMode={mode}
        searchDefault={query}
      />

      <BoardFilterBar
        className="sticky top-16 z-30"
        filters={filters}
        onChange={setFilters}
        divOptions={divOptions}
        savedCount={shortlist.count}
        shownCount={visible.length}
        totalCount={results.length}
      />

      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 pb-16">
        {mock && (
          <p className="pt-4 text-[12px] font-bold text-gc-ink-2">
            <span aria-hidden>※ </span>
            예시 데이터로 표시 중입니다 — 실제 조회 결과가 아닙니다.
          </p>
        )}
        {/* 총평 */}
        {mode === "company" && (
          <div className="pt-6">
            {summary ? (
              <p className="text-[14.5px] leading-[1.8] text-gc-ink-2 break-keep max-w-[72ch]">
                <b className="font-gc-serif font-black text-gc-ink text-[15.5px] mr-2">
                  총평
                </b>
                {summary}
              </p>
            ) : (
              !streamDone &&
              data.algorithm === "v2" && (
                <p className="text-[13px] text-gc-ink-3">총평 작성 중…</p>
              )
            )}
            <p className="mt-2.5 text-[12px] text-gc-ink-3">
              <span aria-hidden>※ </span>
              적합도는 검토 우선순위이며 낙찰 가능성이 아닙니다.
            </p>
          </div>
        )}
        {mode === "keywords" && (
          <p className="pt-6 text-[12px] text-gc-ink-3">
            <span aria-hidden>※ </span>
            적합도는 검토 우선순위이며 낙찰 가능성이 아닙니다.
          </p>
        )}

        {/* 개찰판 본체 */}
        {results.length === 0 ? (
          <EmptyBoard
            text={
              data.error
                ? `조회 실패: ${data.error}`
                : "조건에 맞는 공고를 찾지 못했습니다. 키워드를 넓히거나 다른 모드로 시도해보세요."
            }
          />
        ) : (
          <section className="mt-5">
            <ColumnHead />
            {visible.length === 0 ? (
              <div className="border-b border-gc-rule py-10 text-center">
                <p className="text-[14px] text-gc-ink-2">
                  조건에 맞는 행이 없습니다.
                </p>
                <button
                  type="button"
                  onClick={() => setFilters(EMPTY_FILTERS)}
                  className="mt-2 text-[13px] font-bold text-gc-ink underline underline-offset-2 hover:text-gc-ink-2"
                >
                  조건 해제
                </button>
              </div>
            ) : (
              <ol>
                {visible.map(({ bid, rank }) => (
                  <BoardRow
                    key={bidKey(bid)}
                    bid={withExplanation(bid)}
                    rank={rank}
                    open={openKeys.has(bidKey(bid))}
                    onToggle={() => toggleOpen(bid, rank)}
                    saved={shortlist.has(bidKey(bid))}
                    onToggleSave={() => toggleSave(bid, rank)}
                    primary={rank <= TOP_N}
                    explanationPending={!streamDone}
                  />
                ))}
              </ol>
            )}
            {isFiltered(filters) && visible.length > 0 && (
              <p className="mt-3 text-[12px] text-gc-ink-3">
                <span aria-hidden>※ </span>
                순번은 전체 판 기준입니다. 조건에 걸러진 행은 표시되지 않습니다.
              </p>
            )}
          </section>
        )}

        <PreSpecBoard results={data.pre_spec_results ?? []} />
        <OrderPlanBoard results={data.order_plan_results ?? []} />

        {mode === "keywords" && (
          <KeywordPanel
            title="다른 키워드로도 찾아볼까요?"
            defaultQuery={query}
            className="mt-12"
          />
        )}
      </div>

      <SubscribeBand />
    </div>
  );
}

/* ── 판머리 ─────────────────────────────────────────────── */

function BoardHead({
  title,
  meta,
  criteria,
  count,
  date,
  searchMode,
  searchDefault,
}: {
  title: string;
  meta: (string | null)[];
  criteria: string;
  count?: number;
  date: string;
  searchMode: Mode;
  searchDefault?: string;
}) {
  const metaItems = meta.filter(Boolean) as string[];
  return (
    <section className="bg-gc-band">
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-7 sm:pt-9 pb-6 sm:pb-8">
        <div className="flex items-start justify-between gap-5">
          <div className="min-w-0">
            <h1 className="font-gc-serif font-black text-[30px] sm:text-[42px] leading-[1.2] tracking-[-0.02em] text-gc-band-hi break-keep">
              {title}
              {count !== undefined && (
                <span className="ml-3 align-middle text-[15px] sm:text-[17px] font-bold text-gc-band-ink whitespace-nowrap">
                  검토 우선순위 {count}건
                </span>
              )}
            </h1>
            <p className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12.5px] sm:text-[13px] text-gc-band-ink">
              {metaItems.map((m) => (
                <span key={m} className="font-semibold">
                  {m}
                </span>
              ))}
              {metaItems.length > 0 && <span aria-hidden>|</span>}
              <span>{criteria}</span>
            </p>
            <p className="mt-1 text-[12px] tabular tabular-nums text-gc-band-ink">
              {date} 조회 · 매일 갱신 · 나라장터 기반
            </p>
          </div>
          <div className="hidden sm:flex flex-col items-end gap-4 shrink-0">
            <BoardSeal size={62} />
            <BoardSearch variant="compact" initialMode={searchMode} defaultValue="" />
          </div>
          <BoardSeal size={44} className="sm:hidden shrink-0 mt-1" />
        </div>
        <div className="sm:hidden mt-4">
          <BoardSearch variant="compact" initialMode={searchMode} defaultValue={searchDefault ?? ""} />
        </div>
      </div>
    </section>
  );
}

/* ── 판 컬럼 머리 (데스크톱) ────────────────────────────── */

function ColumnHead() {
  return (
    <div
      aria-hidden
      className="hidden sm:grid grid-cols-[48px_minmax(0,1fr)_84px_104px_120px_28px] gap-x-4 px-1 pb-2 border-b-2 border-gc-ink text-[11.5px] font-bold text-gc-ink-2"
    >
      <span className="text-right pr-1">순번</span>
      <span>공고</span>
      <span className="text-right">마감</span>
      <span className="text-right">추정가</span>
      <span className="text-right">적합</span>
      <span />
    </div>
  );
}

function EmptyBoard({ text }: { text: string }) {
  return (
    <div className="mt-5 border-y-2 border-gc-ink py-12 text-center">
      <p className="text-[15px] font-semibold text-gc-ink-2 break-keep">{text}</p>
    </div>
  );
}

/* ── 사전규격 판 ────────────────────────────────────────── */

function PreSpecBoard({ results }: { results: PreSpecRecommendation[] }) {
  if (results.length === 0) return null;
  const sorted = [...results]
    .sort((a, b) => {
      const da = daysUntil(a.opnin_rgst_clse_dt);
      const db = daysUntil(b.opnin_rgst_clse_dt);
      const ac = da !== null && da >= 0 && da <= 2 ? 1 : 0;
      const bc = db !== null && db >= 0 && db <= 2 ? 1 : 0;
      if (ac !== bc) return bc - ac;
      return (b.score ?? 0) - (a.score ?? 0);
    })
    .slice(0, 5);

  return (
    <section className="mt-14">
      <SectionHead
        title={`사전규격 — 지금 의견 낼 수 있는 ${sorted.length}건`}
        note="본공고 전 단계. 사양이 굳기 전에 의견을 낼 수 있는 마지막 시점입니다."
      />
      <ol>
        {sorted.map((spec, i) => {
          const d = daysUntil(spec.opnin_rgst_clse_dt);
          const urgent = d !== null && d >= 0 && d <= 2;
          return (
            <li
              key={spec.bf_spec_rgst_no}
              className="grid grid-cols-[40px_minmax(0,1fr)_auto] sm:grid-cols-[48px_minmax(0,1fr)_120px_104px] items-baseline gap-x-4 px-1 py-3 border-b border-gc-rule"
            >
              <span className="text-right pr-1 text-[14px] font-bold tabular tabular-nums text-gc-ink-2">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                <span className="block text-[14.5px] font-bold text-gc-ink leading-[1.45] break-keep">
                  {spec.prdct_clsfc_no_nm || spec.prdct_dtl_list || "품명 미상"}
                </span>
                <span className="mt-0.5 block text-[12.5px] text-gc-ink-3">
                  {spec.rl_dminstt_nm || spec.order_instt_nm || "—"}
                </span>
              </span>
              <span className="text-right text-[13px] self-start">
                <span
                  className={cn(
                    "font-bold tabular tabular-nums",
                    urgent ? "text-gc-injuk" : "text-gc-ink"
                  )}
                >
                  {d === null
                    ? "—"
                    : d < 0
                      ? "마감"
                      : d === 0
                        ? "의견 오늘 마감"
                        : `의견 D-${d}`}
                </span>
              </span>
              <span className="hidden sm:block text-right text-[13.5px] font-semibold tabular tabular-nums text-gc-ink self-start">
                {formatKRW(spec.asign_bdgt_amt)}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/* ── 발주계획 판 ────────────────────────────────────────── */

function OrderPlanBoard({ results }: { results: OrderPlanRecommendation[] }) {
  const top = results
    .filter((p) => !isPastPlan(p))
    .slice(0, 5);
  if (top.length === 0) return null;
  return (
    <section className="mt-14">
      <SectionHead
        title={`발주계획 — 선행 신호 ${top.length}건`}
        note="사양 미확정 단계. 본공고까지 1~3개월 여유가 있는 사전 신호입니다."
      />
      <ol>
        {top.map((plan, i) => (
          <li
            key={plan.order_plan_unty_no}
            className="grid grid-cols-[40px_minmax(0,1fr)_auto] sm:grid-cols-[48px_minmax(0,1fr)_120px_104px] items-baseline gap-x-4 px-1 py-3 border-b border-gc-rule"
          >
            <span className="text-right pr-1 text-[14px] font-bold tabular tabular-nums text-gc-ink-2">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="min-w-0">
              <span className="block text-[14.5px] font-bold text-gc-ink leading-[1.45] break-keep">
                {plan.biz_nm || plan.prdct_clsfc_no_nm || "사업명 미상"}
              </span>
              <span className="mt-0.5 block text-[12.5px] text-gc-ink-3">
                {plan.order_instt_nm || plan.totlmng_instt_nm || "—"}
              </span>
            </span>
            <span className="text-right text-[13px] font-bold tabular tabular-nums text-gc-ink self-start">
              {plan.order_year && plan.order_mnth
                ? `${plan.order_year}.${String(plan.order_mnth).padStart(2, "0")} 예정`
                : "시기 미상"}
            </span>
            <span className="hidden sm:block text-right text-[13.5px] font-semibold tabular tabular-nums text-gc-ink self-start">
              {formatKRW(plan.sum_order_amt)}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** 이미 지난 발주 예정월은 선행 신호가 아님 — 노출 제외 */
function isPastPlan(p: OrderPlanRecommendation) {
  if (!p.order_year || !p.order_mnth) return false;
  const now = new Date();
  const ym = Number(p.order_year) * 12 + Number(p.order_mnth);
  const cur = now.getFullYear() * 12 + (now.getMonth() + 1);
  return ym < cur;
}

function SectionHead({ title, note }: { title: string; note: string }) {
  return (
    <div className="gc-double-rule pt-3 pb-2.5 mb-0.5">
      <h2 className="font-gc-serif font-black text-[19px] sm:text-[21px] tracking-[-0.02em] text-gc-ink">
        {title}
      </h2>
      <p className="mt-1 text-[12.5px] text-gc-ink-3 break-keep">{note}</p>
    </div>
  );
}

/* ── 키워드 재조회 패널 ─────────────────────────────────── */

const SUGGESTED_KEYWORDS = [
  "정보시스템 유지보수",
  "AI 데이터 분석",
  "위탁교육 직무역량",
  "시설물 유지관리",
  "콘텐츠 영상 제작",
  "보안 컨설팅",
  "급식 식자재",
  "조경 관리",
];

function KeywordPanel({
  title,
  lead,
  defaultQuery = "",
  className,
}: {
  title: string;
  lead?: string;
  defaultQuery?: string;
  className?: string;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [value, setValue] = useState(defaultQuery);
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    setLoading(true);
    const next = new URLSearchParams();
    next.set("q", q);
    next.set("mode", "keywords");
    const company = params.get("company");
    if (company) next.set("company", company);
    router.push(`/recommendations?${next.toString()}`);
  };

  const addKeyword = (kw: string) => {
    setValue((cur) => {
      const cleaned = cur.trim();
      if (!cleaned) return kw;
      if (cleaned.toLowerCase().includes(kw.toLowerCase())) return cleaned;
      return `${cleaned}, ${kw}`;
    });
  };

  return (
    <section className={cn("gc-double-rule pt-4", className)}>
      <h2 className="font-gc-serif font-black text-[20px] sm:text-[22px] tracking-[-0.02em] text-gc-ink">
        {title}
      </h2>
      {lead && (
        <p className="mt-2 text-[14px] leading-[1.7] text-gc-ink-2 break-keep max-w-[60ch]">
          {lead}
        </p>
      )}
      <form onSubmit={submit} className="mt-5 max-w-[640px]">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="예) AI 콜센터 구축, 교육청 시스템 유지보수, 클라우드 마이그레이션"
          rows={2}
          className="w-full bg-gc-sheet border border-gc-rule rounded-[3px] px-4 py-3 text-[14.5px] font-medium text-gc-ink placeholder:text-gc-ink-3 placeholder:font-normal outline-none resize-none focus:border-gc-ink transition-colors"
        />
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          {SUGGESTED_KEYWORDS.map((kw) => (
            <button
              key={kw}
              type="button"
              onClick={() => addKeyword(kw)}
              className="px-2.5 py-1 text-[12px] font-semibold text-gc-ink-2 border border-gc-rule rounded-full bg-gc-sheet hover:border-gc-ink hover:text-gc-ink transition-colors"
            >
              + {kw}
            </button>
          ))}
        </div>
        <button
          type="submit"
          disabled={!value.trim() || loading}
          className="mt-4 h-11 px-5 bg-gc-band text-gc-band-hi text-[14.5px] font-bold rounded-[3px] disabled:opacity-40 hover:bg-gc-ink transition-colors"
        >
          {loading ? "대조 중…" : "이 키워드로 조회"}
        </button>
      </form>
    </section>
  );
}

/* ── 회사 미식별 폴백 ───────────────────────────────────── */

function FallbackBoard({
  query,
  identified,
  message,
}: {
  query: string;
  identified: boolean;
  message?: string | null;
}) {
  const today = new Date().toLocaleDateString("ko-KR");
  return (
    <div className="world-gc flex-1">
      <BoardHead
        title={query}
        meta={[identified ? "회사 식별 완료" : "회사 식별 실패"]}
        criteria={
          identified
            ? "회사 데이터가 부족해 정확도가 낮을 수 있습니다"
            : "나라장터 회사 명부에서 찾지 못했습니다"
        }
        date={today}
        searchMode="company"
        searchDefault={query}
      />
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 pb-16">
        {message && (
          <p className="pt-6 text-[13px] text-gc-ink-3 break-keep">
            <span aria-hidden>※ </span>
            {message}
          </p>
        )}
        <KeywordPanel
          className="mt-10"
          title="관심 영역을 직접 알려주세요"
          lead="회사 데이터 대신 키워드로 대조합니다. 관심 영역을 입력하면 의미가 가까운 공고를 바로 찾아드립니다."
        />
      </div>
      <SubscribeBand />
    </div>
  );
}

/* ── 연결 오류 ──────────────────────────────────────────── */

function ConnectionErrorBoard({ query }: { query: string }) {
  return (
    <div className="world-gc flex-1">
      <div className="mx-auto max-w-[560px] px-5 py-24 sm:py-32 text-center">
        <p className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
          연결이 잠시 원활하지 않습니다
        </p>
        <p className="mt-3 text-[14.5px] leading-[1.7] text-gc-ink-2 break-keep">
          서버가 준비되는 중일 수 있어요. 잠시 후 다시 시도하면 대부분
          해결됩니다.
          {query && (
            <>
              {" "}
              (<b className="text-gc-ink">{query}</b> 조회)
            </>
          )}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-7 inline-flex items-center h-11 px-5 bg-gc-band text-gc-band-hi text-[14.5px] font-bold rounded-[3px] hover:bg-gc-ink transition-colors"
        >
          다시 시도
        </button>
      </div>
    </div>
  );
}

/* ── 대조 중 ────────────────────────────────────────────── */

function BoardLoading({ label, mode }: { label: string; mode: Mode }) {
  return (
    <div className="world-gc flex-1">
      <div className="mx-auto max-w-[560px] px-5 py-24 sm:py-32 text-center">
        <p className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
          {label}
        </p>
        <p className="mt-3 text-[14.5px] text-gc-ink-2 break-keep">
          나라장터 공고와 {mode === "company" ? "회사 정보" : "검색 키워드"}를
          대조하고 있습니다.
        </p>
        <div
          className="relative mt-7 h-px bg-gc-rule overflow-hidden"
          role="status"
          aria-label="대조 진행 중"
        >
          <span className="gc-scan-bar absolute inset-y-0 left-0 w-1/4 bg-gc-ink" />
        </div>
        <p className="mt-3 text-[12.5px] tabular tabular-nums text-gc-ink-3">
          보통 5~12초 소요됩니다.
        </p>
      </div>
    </div>
  );
}
