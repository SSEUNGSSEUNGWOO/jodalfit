// frontend/src/components/results/ResultsView.tsx
// 결과 페이지 본체(클라이언트). 상태: running(장면) → done(표) / zero / error / search(다른 회사). 키워드 모드는 장면 없이 표만.
"use client";

import { useEffect, useState } from "react";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { Btn } from "@/components/Btn";
import { SearchBox } from "@/components/SearchBox";
import { StarCompany } from "@/components/StarCompany";
import { streamRecommendations } from "@/lib/stream";
import { getSessionId } from "@/lib/events";
import { cn, maskBizrno } from "@/lib/utils";
import { companyStats } from "@/lib/saved-stats";
import { kstDate } from "@/lib/format";
import type { CompanyDigest, RecommendationResponse } from "@/types/recommendations";
import { Scene, type SceneCounts } from "./Scene";
import { FunnelLine } from "./FunnelLine";
import { LeadsLine } from "./LeadsLine";
import { rememberCompany } from "@/components/entry/RecentChips";
import { CompanySide } from "./CompanySide";
import { ResultRows, ZeroBlock } from "./ResultRows";

const TIMEOUT_MS = 8000;
// 20 건 — 채점표 K 곡선(12→20 은 낙찰 포함률이 크게 오르고 20→30 은 거의 안 는다)과 실사용 로그(13~20위에서 저장의 27%)를 같이 보고 정했다. 2026-10-23.
// 공개 5 + 흐림 미리보기 3. 인쇄 보고서는 A4 한 장에 맞춰 12 건으로 따로 간다(report/page.tsx).
const RESULT_LIMIT = 20;
const EMPTY: SceneCounts = { total: null, candidates: null, passed: null, results: null };
const OTHER = "ml-3.5 cursor-pointer border-b border-field text-[13px] font-medium text-ink-g hover:border-orange";

export function ResultsView({ query, mode, keywords, algorithm, from, loggedIn, savedKeys, reviewedKeys, next, initialCompany }: {
  query: string; mode: "company" | "keywords"; keywords: string | null; algorithm: "v1" | "v2"; from: string | null;
  loggedIn: boolean; savedKeys: string[]; reviewedKeys: string[]; next: string; initialCompany?: CompanyDigest | null;
}) {
  const [counts, setCounts] = useState<SceneCounts>(EMPTY);
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errStatus, setErrStatus] = useState<number | null>(null); // 404 = 재시도로 못 푸는 상태(회사 없음·벡터 없음) → 다시 시도 대신 다른 검색
  const [settled, setSettled] = useState(mode === "keywords");
  const [search, setSearch] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [today] = useState(() => new Date()); // 렌더 동안 읽히는 값 — ref 가 아니라 state(react-hooks/refs)

  // 질의가 바뀌면 페이지가 key 로 다시 마운트한다 — 효과 안에서 상태를 초기화하지 않는다(재시도는 버튼 핸들러가 비운다).
  useEffect(() => {
    const ac = new AbortController();
    let got = false;
    const timer = setTimeout(() => { if (!got) { ac.abort(); setError("결과를 불러오지 못했습니다"); } }, TIMEOUT_MS);
    streamRecommendations(
      { query, mode, keywords, algorithm, session_id: getSessionId(), limit: RESULT_LIMIT, candidate_pool: 200, explain_top: 0, with_explanation: false },
      (e) => {
        // 0057 부터 funnel 은 total 하나만 준다 — 등록업종 허용 수는 깔때기의 칸이 아니었다(Scene.tsx 주석).
        if (e.type === "funnel") setCounts((c) => ({ ...c, total: e.total }));
        else if (e.type === "stage" && e.stage === "search") setCounts((c) => ({ ...c, candidates: e.candidates }));
        else if (e.type === "stage" && e.stage === "qualify") setCounts((c) => ({ ...c, candidates: e.candidates, passed: e.passed }));
        else if (e.type === "stage" && e.stage === "rank") setCounts((c) => ({ ...c, results: e.results }));
        // passed 를 0 으로 메우지 않는다 — 0056 미적용·v1 이면 모르는 값이고 "면허·지역 0% 통과"는 거짓이다. Scene 은 results 만으로 끝낸다.
        else if (e.type === "results") { got = true; clearTimeout(timer); setData(e.data); setCounts((c) => ({ ...c, results: e.data.results.length })); }
        else if (e.type === "error") { got = true; clearTimeout(timer); setError(e.message); setErrStatus(e.status ?? null); }
      },
      ac.signal,
    ).catch((err) => { if (!ac.signal.aborted && !got) { clearTimeout(timer); setError(String(err?.message || "결과를 불러오지 못했습니다")); } });
    return () => { clearTimeout(timer); ac.abort(); };
  }, [query, mode, keywords, algorithm, attempt]);

  // 회사 모드인데 회사를 못 찾았으면 키워드로 넘어간다(옛 보드와 같은 규칙)
  useEffect(() => {
    if (mode === "company" && data && !data.company && data.fallback === "keywords") {
      location.replace(`/recommendations?q=${encodeURIComponent(query)}&from=company`);
    }
  }, [data, mode, query]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSearch(false); };
    addEventListener("keydown", onKey); return () => removeEventListener("keydown", onKey);
  }, []);

  const co = data?.company ?? initialCompany ?? null;

  // 회사를 확정하면 입구의 '최근 조회' 에 남긴다 — 다시 치지 않게. 브라우저에만 남는다.
  useEffect(() => {
    if (co?.corp_nm) rememberCompany({ nm: co.corp_nm, rgn: co.rgn_nm ?? undefined });
  }, [co?.corp_nm, co?.rgn_nm]);
  const bizrno = co ? co.bizrno.replace(/\D/g, "") : null;
  const results = data?.results ?? [];
  const state: "running" | "done" | "error" = error ? "error" : settled && data ? "done" : "running";
  const zero = state === "done" && results.length === 0;
  const stats = results.length ? companyStats(results.map((r) => r.bid_clse_date), today) : null;

  return (
    <div className={cn(search && "[&_[data-scene]]:opacity-20 [&_[data-scene]]:blur-[1px] [&_[data-res]]:opacity-20 [&_[data-res]]:blur-[1px] [&_[data-res]]:pointer-events-none")}>
      {search ? (
        <div className="pb-1 pt-[26px]" data-search>
          <SearchBox autoFocus onSubmitted={() => setSearch(false)} />
          <div className="mt-2.5 flex max-w-[720px] items-center gap-3.5 text-[13px] text-ink-g">
            <span className="t-k">최근 조회</span>
            {co && <a className="border-b border-field text-ink" href={`/recommendations?company=${encodeURIComponent(co.bizrno)}`}>{co.corp_nm}</a>}
            <button type="button" className="ml-auto cursor-pointer text-ink-mute" onClick={() => setSearch(false)}>취소 · Esc</button>
          </div>
        </div>
      ) : mode === "company" ? (
        <PageHead title={co?.corp_nm ?? query} small={co ? maskBizrno(co.bizrno) : undefined} className="border-b-0! pb-0"
          aside={<>
            {bizrno && <StarCompany bizrnoNorm={bizrno} saved={savedKeys.includes(bizrno)} loggedIn={loggedIn} next={next} className="ml-3 h-[30px] text-[13px]" />}
            <button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 회사</button>
          </>}
          meta={co ? [co.rgn_nm ?? "—", `기준일 ${kstDate(today)}`] : undefined} />
      ) : (
        <PageHead title={`“${query}”`} className="border-b-0! pb-0" aside={<button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 검색</button>}
          meta={[from === "company" ? "회사명으로 찾지 못해 키워드로 검색" : "입력한 관심 분야와 의미가 가까운 순서"]} />
      )}

      {mode === "company" && <Scene key={attempt} playbackKey={JSON.stringify([query, keywords, algorithm])} counts={counts} state={state} onSettled={() => setSettled(true)} />}
      {mode === "keywords" && <div className="mt-5 border-t border-ink" />}

      {error && (
        <div data-err className="flex items-center gap-3.5 border-t border-hair py-4 text-[13.5px] text-ink">
          <span>{errStatus === 404 ? error : "결과를 불러오지 못했습니다"}</span><span className="flex-1" />
          {errStatus === 404 ? (
            <Btn onClick={() => setSearch(true)}>다른 검색</Btn>
          ) : (
            <Btn onClick={() => {
              setCounts(EMPTY); setData(null); setError(null); setErrStatus(null);
              setSettled(mode === "keywords"); setAttempt((a) => a + 1);
            }}>다시 시도</Btn>
          )}
        </div>
      )}

      {mode === "company" && !error && (
        <FunnelLine counts={counts} open={state === "done"} />
      )}

      {state === "done" && data && (
        <Panel data-res className="mt-4 translate-y-0 opacity-100 transition-[opacity,transform] duration-500 [transition-timing-function:var(--ease-sheet)] starting:translate-y-2.5 starting:opacity-0">
          <div className="pt-6 max-sm:pt-5">
            {!zero && (
              <div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3 border-b border-ink pb-5 max-sm:pb-4">
                <div>
                  <h2 className="text-[24px] font-semibold tracking-[-0.035em] text-ink max-sm:text-[21px]">검토할 공고 <span className="num">{results.length}</span><span className="ml-0.5 text-[16px] font-medium">건</span></h2>
                  <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-g">
                    <span>{mode === "company" ? "적합 순" : "검색어 유사도 순"}</span>
                    {stats && stats.week > 0 && <span>이번 주 마감 <b className="num font-semibold text-ink">{stats.week}건</b></span>}
                  </p>
                </div>
                {mode === "company" && co && <a href={loggedIn ? `/recommendations/report?company=${encodeURIComponent(co.bizrno)}` : `/login?next=${encodeURIComponent(`/recommendations/report?company=${co.bizrno}`)}`} className="inline-flex h-9 items-center gap-2 rounded-[6px] border border-field px-3 text-[12.5px] font-medium text-ink-g transition-colors hover:border-ink max-sm:h-8"><span className="max-sm:hidden">인쇄 / PDF 저장</span><span className="hidden max-sm:inline">PDF 저장</span><span aria-hidden="true">↗</span></a>}
              </div>
            )}
            {zero ? <ZeroBlock reason={counts.passed === 0 ? "qualify" : "rank"} viaBizrno={bizrno} />
                  : <ResultRows results={results} loggedIn={loggedIn} reviewed={new Set(reviewedKeys)} viaBizrno={bizrno} next={next} today={today} keywordMode={mode === "keywords"} />}
            {mode === "company" && (
              <LeadsLine preSpecs={data.pre_spec_results ?? []} orderPlans={data.order_plan_results ?? []} />
            )}
            {mode === "company" && bizrno && <CompanySide bizrnoNorm={bizrno} region={co?.rgn_nm ?? null} />}
          </div>
        </Panel>
      )}
    </div>
  );
}
