// frontend/src/components/results/ResultsView.tsx
// 결과 페이지 본체(클라이언트). 상태: running(장면) → done(표) / zero / error / search(다른 회사). 키워드 모드는 장면 없이 표만.
"use client";

import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { Btn } from "@/components/Btn";
import { SearchSuggest } from "@/components/entry/SearchSuggest";
import { StarCompany } from "@/components/StarCompany";
import { streamRecommendations } from "@/lib/stream";
import { getSessionId } from "@/lib/events";
import { cn, maskBizrno } from "@/lib/utils";
import { companyStats } from "@/lib/saved-stats";
import { kstDate } from "@/lib/format";
import type { CompanyDigest, KeywordFilter, RecommendationResponse } from "@/types/recommendations";
import { Scene, type SceneCounts } from "./Scene";
import { FunnelLine } from "./FunnelLine";
import { LeadsLine } from "./LeadsLine";
import { rememberCompany } from "@/components/entry/RecentChips";
import { CompanySide } from "./CompanySide";
import { ResultRows, ZeroBlock } from "./ResultRows";
import { TitleMatches } from "./TitleMatches";
import { KeywordFilters, NO_FILTER, hasFilter } from "./KeywordFilters";
import { HelpfulLine } from "./HelpfulLine";

const TIMEOUT_MS = 8000;
// 20 건 — 채점표 K 곡선(12→20 은 낙찰 포함률이 크게 오르고 20→30 은 거의 안 는다)과 실사용 로그(13~20위에서 저장의 27%)를 같이 보고 정했다. 2026-10-23.
// 공개 5 + 흐림 미리보기 3. 인쇄 보고서는 A4 한 장에 맞춰 12 건으로 따로 간다(report/page.tsx).
const RESULT_LIMIT = 20;
const EMPTY: SceneCounts = { total: null, candidates: null, passed: null, results: null };
// 같은 탭에서 다시 연 검색은 받아 둔 결과로 바로 — 계산이 없으면 가림막(머리 장면)도 없다(docs/design/README.md
// "머리 장면 = 로딩 가림막"). 공고는 매시 수집되므로 30분이 지나면 다시 계산한다. 2026-10-24.
const CACHE_MS = 30 * 60 * 1000;
type Cached = { at: number; data: RecommendationResponse; counts: SceneCounts };
const OTHER = "ml-3.5 cursor-pointer border-b border-field text-[13px] font-medium text-ink-g hover:border-orange";

export function ResultsView({ query, mode, keywords, algorithm, from, filter = NO_FILTER, loggedIn, savedKeys, reviewedKeys, next, initialCompany }: {
  query: string; mode: "company" | "keywords"; keywords: string | null; algorithm: "v1" | "v2"; from: string | null; filter?: KeywordFilter;
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
  const [cached, setCached] = useState(false);
  const [checked, setChecked] = useState(false); // 캐시를 본 뒤에야 장면을 그린다 — 안 그러면 캐시 히트에도 첫 프레임이 비친다
  const cacheKey = `jf:reco:${mode}:${query}:${keywords ?? ""}:${algorithm}:${filter.div ?? ""}:${filter.due ?? ""}`;
  // 사업자번호로 찾지 못해 키워드로 넘어온 경우 — 숫자를 키워드로 검색해 봐야 뜻이 없다. 계산하지 않고 "다음 시간부터 검색된다"를 적는다.
  // 번호 검색 실패는 시간 잡(register_searched_companies)이 조달청 API 로 등록한다(2026-10-26 (주)에이데이타가 그렇게 들어왔다).
  const noBizrno = mode === "keywords" && from === "company" && isBizrnoLike(query);

  // 질의가 바뀌면 페이지가 key 로 다시 마운트한다 — 효과 안에서 상태를 초기화하지 않는다(재시도는 버튼 핸들러가 비운다).
  useEffect(() => {
    if (noBizrno) { queueMicrotask(() => setChecked(true)); return; }
    let hit: Cached | null = null;
    try {
      const v = JSON.parse(sessionStorage.getItem(cacheKey) ?? "null") as Cached | null;
      if (v && Date.now() - v.at < CACHE_MS) hit = v;
    } catch { /* 저장소가 막혀 있으면 그냥 계산한다 */ }
    if (hit) {
      const h = hit;
      queueMicrotask(() => { setCached(true); setData(h.data); setCounts(h.counts); setSettled(true); setChecked(true); });
      return;
    }
    queueMicrotask(() => setChecked(true));
    const ac = new AbortController();
    let got = false;
    const timer = setTimeout(() => { if (!got) { ac.abort(); setError("결과를 불러오지 못했습니다"); } }, TIMEOUT_MS);
    streamRecommendations(
      { query, mode, keywords, algorithm, session_id: getSessionId(), limit: RESULT_LIMIT, candidate_pool: 200, explain_top: 0, with_explanation: false, div: filter.div, due: filter.due },
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
  }, [query, mode, keywords, algorithm, filter.div, filter.due, attempt, cacheKey, noBizrno]);

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
  // 키워드 모드 첫 판 — 제목에 낱말이 든 공고 전부. 의미 유사 20건(results)은 이것을 뺀 "그 밖에"다(backend _recommend_by_keywords). 2026-10-27
  const titles = mode === "keywords" ? (data?.title_matches ?? []) : [];
  const state: "running" | "done" | "error" = error ? "error" : settled && data ? "done" : "running";
  const zero = state === "done" && results.length === 0 && titles.length === 0;
  const trackedView = useRef(false);
  useEffect(() => {
    if (state !== "done" || !data || trackedView.current) return;
    trackedView.current = true;
    track("results_view", { mode, result_count: results.length + titles.length, logged_in: loggedIn ? 1 : 0, cached: cached ? 1 : 0 });
  }, [state, data, mode, results.length, titles.length, loggedIn, cached]);
  const filtered = mode === "keywords" && hasFilter(filter);   // 칩으로 좁혀 0건이면 "없다"가 아니라 "조건에 없다"
  // 회사는 찾았는데 등록업종·공급물품이 없어 회사 기준 추천이 안 되는 경우(백엔드 fallback=keywords, 7일 27건 = 빈손 검색의 1/3).
  // 전엔 "참가 자격이 있는 공고가 없습니다"(ZeroBlock)로 보여 사실과 달랐다 — 자격을 본 게 아니라 기준이 없었던 것.
  const noInfo = zero && !!data?.error && data?.fallback === "keywords" && !!data?.company;

  // 계산해서 받은 결과만 남긴다. 회사를 못 찾아 키워드로 넘어가는 응답은 남기지 않는다(곧 다른 주소로 간다).
  useEffect(() => {
    if (state !== "done" || cached || !data || (mode === "company" && !data.company)) return;
    try { sessionStorage.setItem(cacheKey, JSON.stringify({ at: Date.now(), data, counts } satisfies Cached)); } catch { /* 용량 초과 등 — 다음에 다시 계산할 뿐 */ }
  }, [state, cached, data, counts, mode, cacheKey]);
  const stats = results.length ? companyStats(results.map((r) => r.bid_clse_date), today) : null;

  return (
    <div className={cn(search && "[&_[data-scene]]:opacity-20 [&_[data-scene]]:blur-[1px] [&_[data-res]]:opacity-20 [&_[data-res]]:blur-[1px] [&_[data-res]]:pointer-events-none")}>
      {search ? (
        <div className="pb-1 pt-[26px]" data-search>
          <SearchSuggest autoFocus initialMode={mode} />
          <div className="mt-2.5 flex max-w-[720px] items-center gap-3.5 text-[13px] text-ink-g">
            <span className="t-k">최근 조회</span>
            {co && <a className="border-b border-field text-ink" href={`/recommendations?company=${encodeURIComponent(co.bizrno)}`}>{co.corp_nm}</a>}
            <button type="button" className="ml-auto cursor-pointer text-ink-mute" onClick={() => setSearch(false)}>취소 · Esc</button>
          </div>
        </div>
      ) : mode === "company" ? (
        <PageHead title={co?.corp_nm ?? query} small={co ? maskBizrno(co.bizrno) : undefined} className="border-b-0! pb-0"
          aside={<>
            {bizrno ? <StarCompany bizrnoNorm={bizrno} saved={savedKeys.includes(bizrno)} loggedIn={loggedIn} next={next} className="ml-3 h-[30px] text-[13px]" />
              : <span aria-hidden="true" className="inline-flex h-[30px] w-0 items-center overflow-hidden text-[13px]">{" "}</span> /* 버튼과 같은 높이·기준선으로 미리 — 도착할 때 제목 줄이 커지지 않게 */}
            <button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 회사</button>
          </>}
          /* 회사 정보는 결과와 함께 온다 — 그 전에도 한 줄 자리를 잡아 둔다(없으면 도착할 때 장면 전체가 30px 내려앉았다) */
          meta={co ? [co.rgn_nm ?? "—", `기준일 ${kstDate(today)}`] : [" "]} />
      ) : (
        <PageHead title={`“${query}”`} className="border-b-0! pb-0" aside={<button type="button" data-other className={OTHER} onClick={() => setSearch(true)}>다른 검색</button>}
          meta={[noBizrno ? "사업자번호로 찾지 못했습니다" : from === "company" ? "회사명으로 찾지 못해 키워드로 검색" : "제목·기관·지역에 든 공고 전부 · 이어서 뜻이 가까운 공고"]} />
      )}

      {mode === "company" && checked && !cached && <Scene key={attempt} counts={counts} state={state} onSettled={() => setSettled(true)} />}
      {(mode === "keywords" || cached) && <div className="mt-5 border-t border-ink" />}

      {noBizrno && (
        <Panel data-res className="mt-4"><div className="pt-6 max-sm:pt-5"><NoBizrnoBlock query={query} /></div></Panel>
      )}

      {/* 오타 등급으로만 잡힌 회사 — 다른 회사일 수 있다. 결과가 온 뒤 머리 아래 한 줄로 알리고 번호 검색으로 보낸다. */}
      {mode === "company" && state === "done" && co?.match === "fuzzy" && (
        <p data-fuzzy className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink">
          <span>‘{query}’와 가장 가까운 이름의 회사로 찾았습니다. 다른 회사면 사업자번호로 검색합니다.</span>
          <button type="button" className="cursor-pointer border-b border-field font-medium text-ink-g hover:border-orange" onClick={() => setSearch(true)}>사업자번호로 검색</button>
        </p>
      )}

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

      {mode === "company" && !error && !noInfo && (
        <FunnelLine counts={counts} open={state === "done"} />
      )}

      {state === "done" && data && !noBizrno && (
        <Panel data-res className="mt-4 translate-y-0 opacity-100 transition-[opacity,transform] duration-500 [transition-timing-function:var(--ease-sheet)] starting:translate-y-2.5 starting:opacity-0">
          <div className="pt-6 max-sm:pt-5">
            {/* 좁히기 칩은 판이 비어도 남는다 — 안 그러면 좁혀서 0건이 된 뒤 되돌릴 길이 없다 */}
            {mode === "keywords" && <KeywordFilters query={query} from={from} filter={filter} />}
            {titles.length > 0 && <TitleMatches rows={titles} terms={data.title_terms ?? [query]} capped={!!data.title_match_capped} loggedIn={loggedIn} reviewed={new Set(reviewedKeys)} next={next} today={today} />}
            {!zero && results.length > 0 && (
              <div className={cn("flex flex-wrap items-start justify-between gap-x-5 gap-y-3 border-b border-ink pb-5 max-sm:pb-4", titles.length > 0 && "mt-12 max-sm:mt-10")}>
                <div>
                  <h2 className="text-[24px] font-semibold tracking-[-0.035em] text-ink max-sm:text-[21px]">{mode === "company" ? "검토할 공고" : titles.length > 0 ? "그 밖에 뜻이 가까운 공고" : "뜻이 가까운 공고"} <span className="num">{results.length}</span><span className="ml-0.5 text-[16px] font-medium">건</span></h2>
                  <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-g">
                    <span>{mode === "company" ? "적합 순" : "검색어 유사도 순"}</span>
                    {stats && stats.week > 0 && <span>이번 주 마감 <b className="num font-semibold text-ink">{stats.week}건</b></span>}
                  </p>
                  {/* 등록업종 0건 회사 — 면허 판정이 전부 '확인불가'로 통과한다(qualifications.py). 그 사실을 적고 감점 사실을 알린다. */}
                  {mode === "company" && co?.industry_count === 0 && (
                    <p data-noind className="mt-2 max-w-[640px] text-[13px] leading-[1.6] text-ink-g">나라장터에 등록업종이 없어 면허 자격을 판정하지 못했습니다. 면허 제한이 있는 공고는 순서를 낮췄습니다.</p>
                  )}
                </div>
                {mode === "company" && co && <a href={loggedIn ? `/recommendations/report?company=${encodeURIComponent(co.bizrno)}` : `/login?next=${encodeURIComponent(`/recommendations/report?company=${co.bizrno}`)}`} className="inline-flex h-9 items-center gap-2 rounded-[6px] border border-field px-3 text-[12.5px] font-medium text-ink-g transition-colors hover:border-ink max-sm:h-8"><span className="max-sm:hidden">인쇄 / PDF 저장</span><span className="hidden max-sm:inline">PDF 저장</span><span aria-hidden="true">↗</span></a>}
              </div>
            )}
            {noInfo ? <NoInfoBlock corpNm={co?.corp_nm ?? query} />
                  : zero && filtered ? (
                    <p data-zero data-filtered className="pb-[34px] pt-[22px] text-[14px] leading-[1.7] text-ink-dim">
                      <b className="mr-3 text-[18px] font-[650] tracking-[-0.015em] text-ink">좁힌 조건에 맞는 공고가 없습니다</b>
                      <a href={`/recommendations?q=${encodeURIComponent(query)}${from ? `&from=${encodeURIComponent(from)}` : ""}`} className="border-b border-field font-medium text-ink-g hover:border-orange">조건 해제</a>
                    </p>
                  )
                  : zero ? <ZeroBlock reason={counts.passed === 0 ? "qualify" : "rank"} viaBizrno={bizrno} />
                  : results.length > 0 && <ResultRows results={results} loggedIn={loggedIn} reviewed={new Set(reviewedKeys)} viaBizrno={bizrno} next={next} today={today} keywordMode={mode === "keywords"} />}
            {/* 키워드 모드에도 — 백엔드는 사전규격·발주계획을 두 모드 다 돌려준다(2026-10-26 전엔 회사 모드만 그렸다). */}
            <LeadsLine preSpecs={data.pre_spec_results ?? []} orderPlans={data.order_plan_results ?? []} />
            {mode === "company" && bizrno && !noInfo && <CompanySide bizrnoNorm={bizrno} region={co?.rgn_nm ?? null} />}
            {!zero && !noInfo && <HelpfulLine mode={mode} query={query} bizrno={bizrno} />}
          </div>
        </Panel>
      )}
    </div>
  );
}

/** 10자리 사업자번호 꼴(숫자·하이픈·공백만)인가 — register_searched_companies 의 _bizrno_input 과 같은 기준 */
function isBizrnoLike(q: string): boolean {
  return /^[\d\-\s]+$/.test(q) && q.replace(/\D/g, "").length === 10;
}

/** 사업자번호로 찾지 못한 회사 — 조달핏에 아직 없는 것이지 자격을 본 게 아니다. 시간 잡이 나라장터에서 가져오므로 그 사실을 적고, 당장은 키워드로 보낸다. */
function NoBizrnoBlock({ query }: { query: string }) {
  return (
    <div data-nobizrno className="pb-[34px] pt-[22px]">
      <b className="block text-[18px] font-[650] tracking-[-0.015em] text-ink">사업자번호 {query}의 회사가 아직 조달핏에 없습니다</b>
      <p className="m-0 mt-1.5 max-w-[640px] text-[14px] leading-[1.7] text-ink-dim">
        나라장터에 등록된 회사면 다음 시간부터 검색됩니다. 지금은 다루는 업종이나 품목을 적어 주시면 그 말뜻으로 공고를 찾습니다.
      </p>
      <div className="mt-[18px] max-w-[720px]"><SearchSuggest autoFocus initialMode="keywords" /></div>
    </div>
  );
}

/** 등록정보가 없는 회사 — 회사 기준 추천은 못 하고, 업종·품목을 적게 해 키워드로 넘긴다. 검색창을 바로 둔다(버튼 하나 더 누르게 하지 않는다). */
function NoInfoBlock({ corpNm }: { corpNm: string }) {
  return (
    <div data-noinfo className="pb-[34px] pt-[22px]">
      <b className="block text-[18px] font-[650] tracking-[-0.015em] text-ink">{corpNm}의 등록업종·공급물품이 나라장터에 없습니다</b>
      <p className="m-0 mt-1.5 max-w-[640px] text-[14px] leading-[1.7] text-ink-dim">
        회사 기준 추천은 등록정보로 자격과 적합도를 판정합니다. 기준이 없으니 다루는 업종이나 품목을 적어 주시면 그 말뜻으로 공고를 찾습니다.
      </p>
      <div className="mt-[18px] max-w-[720px]"><SearchSuggest autoFocus initialMode="keywords" /></div>
      <p className="m-0 mt-3 text-[12.5px] text-ink-mute">나라장터에 업종·물품을 등록하면 다음 날부터 회사 기준으로 추천됩니다.</p>
    </div>
  );
}
