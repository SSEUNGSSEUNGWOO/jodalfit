// frontend/src/components/results/CompanySide.tsx
// 왼쪽 단 — 추천 기준이 되는 회사 정보. 판정 규칙 문구는 시안 그대로(공문 톤).
"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Btn } from "@/components/Btn";
import { rgnBase } from "@/lib/format";
import type { CompanySideData } from "@/app/api/companies/[bizrno]/profile/route";

function dedupeIndustries(names: string[]): string[] {
  const seen = new Set<string>(); const out: string[] = [];
  for (const n of names) { const k = n.split("(")[0].trim(); if (!seen.has(k)) { seen.add(k); out.push(k); } }
  return out;
}

export function CompanySide({ bizrnoNorm, region }: { bizrnoNorm: string; region: string | null }) {
  const [d, setD] = useState<CompanySideData | null>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => {
    const ac = new AbortController();
    fetch(`/api/companies/${bizrnoNorm}/profile`, { signal: ac.signal }).then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    return () => ac.abort();
  }, [bizrnoNorm]);
  useEffect(() => { queueMicrotask(() => { if (matchMedia("(max-width: 639px)").matches) setOpen(false); }); }, []);
  const inds = d ? dedupeIndustries(d.industries) : [];
  const rep = new Set((d?.industries ?? []).slice(0, d?.repCount ?? 0).map((n) => n.split("(")[0].trim()));
  return (
    <details open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} data-side
      className="sticky top-0 pb-5 pt-[22px] text-[14px] max-sm:static max-sm:border-b max-sm:border-rule max-sm:py-3.5 max-sm:text-[13.5px]">
      <summary className="t-k list-none cursor-default max-sm:flex max-sm:cursor-pointer max-sm:justify-between">회사 정보<span className="hidden max-sm:inline">{open ? "접기" : "펼치기"}</span></summary>
      <Sec k={<>등록업종 {d ? inds.length : "…"}{d && d.industries.length > inds.length && <small className="ml-1 text-[12px] font-normal text-ink-mute">세부 {d.industries.length}</small>}</>}>
        <ul className="m-0 list-none p-0">
          {inds.map((n) => (
            <li key={n} className={`border-b border-[#f1f0ec] py-1 leading-[1.5] text-ink-g ${rep.has(n) ? "font-semibold after:ml-1.5 after:text-[10.5px] after:font-medium after:text-ink-mute after:content-['대표']" : ""}`}>{n}</li>
          ))}
        </ul>
      </Sec>
      <Sec k="공급물품">{d && d.products.length > 0 ? `${d.products.length}종` : <><span className="text-ink-dim">등록 없음</span> — 물품 공고 추천에는 등록 필요</>}</Sec>
      <Sec k="지역">본사 <b className="font-semibold text-ink">{rgnBase(region) || "—"}</b><br /><span className="text-ink-dim">제한 공고가 적은 단위(시·도 또는 시·군·구)까지 판정</span></Sec>
      <Sec k="면허">공고 요구 면허 그룹마다 등록업종 중 하나 포함 시 통과</Sec>
      <Sec k="규모"><span className="text-ink-dim">미입력</span> — 소기업·중소기업 제한 공고 판정 기준</Sec>
      <Sec k="사업자 상태">{d ? `${d.status} · ${d.restricted ? "제재 있음" : "제재 없음"}` : "…"}</Sec>
      <div className="mt-[18px] flex items-center gap-2.5 border-t border-hair pt-3.5">
        <Btn variant="dark" className="h-8" href={`/companies/${bizrnoNorm}`}>확인</Btn>
        <Btn variant="text" className="h-8" href="/privacy#request"><u>수정 요청</u></Btn>
      </div>
      <span className="mt-2.5 block text-[12px] text-ink-mute">나라장터 업체정보{d?.checkedAt ? ` · ${d.checkedAt.slice(5).replace("-", ".")} 갱신` : ""}</span>
    </details>
  );
}

function Sec({ k, children }: { k: ReactNode; children: ReactNode }) {
  return (<div className="pt-4 leading-[1.7] text-ink-g"><span className="t-k block">{k}</span><div className="mt-1 text-[14px]">{children}</div></div>);
}
