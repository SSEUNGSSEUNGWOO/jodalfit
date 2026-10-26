"use client";

// 긴 표를 쪽으로 나눠 보여준다 — 사람 검색 200행이 한 화면에 다 깔려 아래 판을 밀어냈다(승우님 2026-10-26).
// 데이터는 서버가 이미 다 넘겼으니 쪽 넘김은 브라우저에서만 한다. 표 모양은 page.tsx 의 Table 과 같다.
import { useState, type ReactNode } from "react";

export function PagedTable({ head, rows, empty, pageSize = 25 }: { head: string[]; rows: ReactNode[][]; empty: string; pageSize?: number }) {
  const [page, setPage] = useState(0);
  if (rows.length === 0) return <p className="m-0 pt-5 text-[14px] text-ink-mute">{empty}</p>;
  const pages = Math.ceil(rows.length / pageSize);
  const cur = Math.min(page, pages - 1);
  const from = cur * pageSize;
  const slice = rows.slice(from, from + pageSize);
  return (
    <div className="overflow-x-auto pt-2" data-paged data-page={cur + 1} data-pages={pages}>
      <table className="w-full border-collapse text-[13.5px] leading-[1.5]">
        <thead>
          <tr className="rule-ink text-left text-[12px] font-semibold text-ink-dim">
            {head.map((h) => <th key={h} className="whitespace-nowrap py-2 pr-4 font-semibold">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {slice.map((r, i) => (
            <tr key={from + i} className="border-b border-rule align-top">
              {r.map((c, j) => <td key={j} className={j === 0 ? "num whitespace-nowrap py-2 pr-4 text-ink-g" : "py-2 pr-4 text-ink"}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {pages > 1 && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px] text-ink-g" data-pager>
          <span className="num">{from + 1}–{from + slice.length} / {rows.length}</span>
          <span className="flex-1" />
          <button type="button" disabled={cur === 0} onClick={() => setPage(cur - 1)} className="cursor-pointer border-b border-field text-ink disabled:cursor-default disabled:border-transparent disabled:text-ink-mute">이전</button>
          {Array.from({ length: pages }, (_, i) => (
            <button key={i} type="button" onClick={() => setPage(i)} aria-current={i === cur ? "page" : undefined}
              className={`num cursor-pointer px-1 ${i === cur ? "font-[650] text-ink" : "text-ink-g hover:text-ink"}`}>{i + 1}</button>
          ))}
          <button type="button" disabled={cur === pages - 1} onClick={() => setPage(cur + 1)} className="cursor-pointer border-b border-field text-ink disabled:cursor-default disabled:border-transparent disabled:text-ink-mute">다음</button>
        </div>
      )}
    </div>
  );
}
