// frontend/src/components/company/CompanyPanels.tsx
// 회사 페이지(06)의 아래 두 판 — 수주 이력 / 낙찰. 시안 company-final 의 판 2·3.
// 서버 컴포넌트: 값은 lib/company.ts 가 읽어 넘긴다.
import type { AwardRow, AwardSummary, ContractRow } from "@/lib/company";
import { cn } from "@/lib/utils";

const nf = new Intl.NumberFormat("ko-KR");

function won(v: number | null): string {
  if (!v) return "—";
  return v >= 100_000_000 ? `${(v / 100_000_000).toFixed(1)}억` : `${nf.format(Math.round(v / 10_000))}만`;
}
const wonFull = (v: number | null) => (v ? `${nf.format(v)}원` : "—");
const ymd = (s: string | null) => (s ? s.slice(0, 10).replace(/-/g, ".") : "—");

export function Panel({ title, meta, children }: { title: string; meta?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="mt-5 rounded-[6px] border border-hair bg-panel px-6 py-5 max-sm:px-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-ink pb-2.5">
        <h2 className="text-[15px] font-[650] text-ink">{title}</h2>
        {meta && <span className="text-[12.5px] text-ink-g">{meta}</span>}
      </div>
      {children}
    </section>
  );
}

export function ContractsPanel({ rows, topInstt }: { rows: ContractRow[]; topInstt: string[] }) {
  if (!rows.length) return null;
  const total = rows.reduce((a, r) => a + (r.cntrct_amt ?? 0), 0);
  const dates = rows.map((r) => r.cntrct_cncls_date).filter(Boolean) as string[];
  const span = dates.length ? `${ymd(dates[dates.length - 1])} ~ ${ymd(dates[0])}` : "—";
  return (
    <Panel
      title="수주 이력"
      meta={
        <>
          계약 {rows.length}건 · {span} · 누적 <b className="num font-[650] text-ink">{won(total)}</b>
          {topInstt.length > 0 && <> · 주요 발주기관 {topInstt.slice(0, 3).join(" · ")}</>}
        </>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13.5px]">
          <thead>
            <tr className="text-[12.5px] text-ink-g">
              <th className="py-1.5 pr-3 text-left font-normal">계약일</th>
              <th className="py-1.5 pr-3 text-left font-normal">사업명 · 계약 방식</th>
              <th className="py-1.5 pr-3 text-left font-normal max-sm:hidden">발주기관</th>
              <th className="py-1.5 text-right font-normal">계약금액</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 10).map((r) => (
              <tr key={r.cntrct_no} className="border-t border-rule align-baseline">
                <td className="num whitespace-nowrap py-2 pr-3 text-ink-g">{ymd(r.cntrct_cncls_date)}</td>
                <td className="py-2 pr-3">
                  <span className="text-ink">{r.cntrct_nm || "—"}</span>
                  {r.bsns_div_nm && <span className="ml-2 text-[12px] text-ink-mute">{r.bsns_div_nm}</span>}
                  <span className="block text-[12px] text-ink-g sm:hidden">{r.dmnd_instt_nm || "—"}</span>
                </td>
                <td className="py-2 pr-3 text-ink-g max-sm:hidden">{r.dmnd_instt_nm || "—"}</td>
                <td className="num whitespace-nowrap py-2 text-right text-ink">{wonFull(r.cntrct_amt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 10 && <p className="mt-2.5 text-[12.5px] text-ink-mute">최근 10건만 표시합니다. 전체 {rows.length}건.</p>}
    </Panel>
  );
}

export function AwardsPanel({ rows, summary }: { rows: AwardRow[]; summary: AwardSummary }) {
  if (!rows.length) return null;
  const rated = rows.filter((r) => typeof r.bid_rate === "number");
  return (
    <Panel
      title="낙찰"
      meta={
        <>
          낙찰 {summary.count}건
          {summary.avg_rate != null && (
            <>
              {" · "}평균 투찰률 <b className="num font-[650] text-ink">{summary.avg_rate.toFixed(1)}%</b>
              <span className="text-ink-mute"> ({rated.length}건 기준)</span>
            </>
          )}
          {summary.total_amt > 0 && <> · 낙찰 총액 {won(summary.total_amt)}</>}
        </>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13.5px]">
          <thead>
            <tr className="text-[12.5px] text-ink-g">
              <th className="py-1.5 pr-3 text-left font-normal">공고 · 마감일</th>
              <th className="py-1.5 pr-3 text-left font-normal max-sm:hidden">발주기관</th>
              <th className="py-1.5 pr-3 text-right font-normal">낙찰가</th>
              <th className="py-1.5 text-right font-normal">투찰률</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 5).map((r) => (
              <tr key={`${r.bid_ntce_no}-${r.bid_ntce_ord}`} className="border-t border-rule align-baseline">
                <td className="py-2 pr-3">
                  <span className="text-ink">{r.bid_ntce_nm || r.bid_ntce_no}</span>
                  <span className="block text-[12px] text-ink-g">
                    마감 {ymd(r.bid_clse_date)}
                    <span className="sm:hidden"> · {r.dmnd_instt_nm || "—"}</span>
                  </span>
                </td>
                <td className="py-2 pr-3 text-ink-g max-sm:hidden">{r.dmnd_instt_nm || "—"}</td>
                <td className="num whitespace-nowrap py-2 pr-3 text-right text-ink">{wonFull(r.bid_amt)}</td>
                <td className="num whitespace-nowrap py-2 text-right">
                  {r.bid_rate == null ? (
                    <span className="text-ink-mute">—</span>
                  ) : (
                    <span className={cn("font-[650]", summary.avg_rate != null && r.bid_rate < summary.avg_rate ? "text-orange" : "text-ink")}>
                      {r.bid_rate.toFixed(1)}%
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2.5 text-[12.5px] leading-[1.7] text-ink-mute">
        투찰률은 낙찰가를 기초금액으로 나눈 값입니다. 공고 원문이 수집되지 않은 건은 &quot;—&quot;로 둡니다. 낙찰은 과거 기록이며 앞으로를
        예측하지 않습니다.
      </p>
    </Panel>
  );
}

export function PeersPanel({ peers }: { peers: { bizrno: string; corp_nm: string; encounter_count: number; sample_notice_names: string[] | null }[] }) {
  if (!peers.length) return null;
  return (
    <Panel title="같은 시장에서 낙찰받는 회사" meta="이 회사가 낙찰받은 공고와 비슷한 공고의 낙찰자">
      <ul>
        {peers.slice(0, 6).map((p) => (
          // 그리드 칸은 기본 min-width:auto 라 긴 공고명이 칸을 밀어낸다 — truncate 가 먹으려면 min-w-0.
          <li key={p.bizrno} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-3 border-b border-rule py-2.5 last:border-0">
            <span className="min-w-0">
              <span className="text-[14px] text-ink">{p.corp_nm}</span>
              {p.sample_notice_names?.[0] && (
                <span className="block truncate text-[12px] text-ink-g">예시 공고 {p.sample_notice_names[0]}</span>
              )}
            </span>
            <span className="num shrink-0 text-[13px] text-ink-g">유사 공고 낙찰 {p.encounter_count}건</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
