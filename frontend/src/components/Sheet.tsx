// frontend/src/components/Sheet.tsx
"use client";

import { useId, useState, type ReactNode } from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[28px_minmax(0,1fr)_84px_84px_110px] gap-x-4 items-start max-sm:grid-cols-[minmax(0,1fr)_auto] max-sm:gap-x-3";

/** 열 머리 — 390 에서는 숨긴다(두 줄 표). */
export function SheetHead({ cols = ["#", "공고 · 발주기관 · 추천 신호", "마감", "추정가", ""] }: { cols?: string[] }) {
  return (
    <div className={cn(GRID, "rule-ink pb-2 pt-2.5 text-[12px] font-semibold text-ink-dim max-sm:hidden")}>
      {cols.map((c, i) => <span key={i} className={i >= 2 ? "text-right" : ""}>{c}</span>)}
    </div>
  );
}

export type SheetRowProps = {
  no: number;
  title: ReactNode;
  org: ReactNode;          // 둘째 줄 왼쪽
  why?: ReactNode;         // 둘째 줄 근거 칩(가장 강한 신호 1개)
  dLeft: { days: number; month: number; day: number } | null;
  price: string;           // won()
  reviewed?: boolean;      // 왼쪽 주황 괘선
  defaultOpen?: boolean;
  children?: ReactNode;    // SheetExpand
  href?: string;           // 제목 링크(공고 상세). 없으면 행 클릭 = 펼침
  onOpen?: () => void;     // 닫힘→열림으로 바뀔 때 한 번 호출
};

/** 표 행 — 제목·마감·금액을 먼저 보여주고, 명시적인 버튼으로 자격·근거를 펼친다. */
export function SheetRow({ no, title, org, why, dLeft, price, reviewed, defaultOpen = false, children, href, onOpen }: SheetRowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const hot = !!dLeft && dLeft.days >= 0 && dLeft.days <= 7;
  const toggle = () => { if (!open) onOpen?.(); setOpen((v) => !v); };
  return (
    <>
      <div data-sheet-row onClick={children ? toggle : undefined}
        className={cn(GRID, "relative border-b border-rule py-5 text-[14px] max-sm:py-[18px]", children && "cursor-pointer transition-colors hover:bg-paper/60",
          "before:absolute before:-left-4 before:top-0 before:bottom-0 before:w-0.5 before:origin-top before:bg-orange before:transition-transform before:duration-300 before:[transition-timing-function:var(--ease-sheet)]",
          reviewed ? "before:scale-y-100" : "before:scale-y-0")}>
        <span className="num pt-[3px] text-[12px] text-ink-mute max-sm:hidden">{String(no).padStart(2, "0")}</span>
        <span className="min-w-0">
          <span className="block break-keep text-[18px] font-semibold leading-[1.5] tracking-[-0.02em] text-ink max-sm:text-[16px]">
            {href ? <Link href={href} onClick={(e) => e.stopPropagation()} className="hover:border-b hover:border-orange">{title}</Link> : title}
          </span>
          <span className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[13px] leading-[1.6] text-ink-g">
            {org}
            {why && <span className="rounded-[4px] border border-hair bg-paper px-1.5 text-[12px] font-medium text-ink-sub">{why}</span>}
          </span>
          <span className="num mt-1.5 hidden text-[13px] text-ink-sub max-sm:block">추정가 <b className="font-semibold text-ink">{price}</b></span>
        </span>
        {dLeft == null ? (
          <span className="num pt-0.5 text-right text-[15px] text-ink-mute">—</span>
        ) : dLeft.days < 0 ? (
          <span className="num pt-0.5 text-right text-[15px] text-ink-mute">
            마감<small className="mt-1 block text-[12px] font-normal">{dLeft.month}.{String(dLeft.day).padStart(2, "0")}</small>
          </span>
        ) : (
          <span className={cn("num pt-0.5 text-right text-[18px] font-semibold tracking-[-0.02em] max-sm:text-[17px]", hot ? "text-orange-ink" : "text-ink")}>
            D-{dLeft.days}<small className="mt-1 block text-[12px] font-normal tracking-normal text-ink-g">{dLeft.month}.{String(dLeft.day).padStart(2, "0")}</small>
          </span>
        )}
        <span className="num pt-0.5 text-right text-[16px] font-medium text-ink max-sm:hidden">{price}</span>
        {children && (
          <button type="button" aria-expanded={open} aria-controls={panelId} aria-label={`${no}번 공고 ${open ? "접기" : "펼치기"}`}
            onClick={(e) => { e.stopPropagation(); toggle(); }}
            className="num mt-0.5 flex w-fit cursor-pointer items-center gap-2 rounded-[5px] border border-field px-2.5 py-1.5 text-[12px] font-medium text-ink-g hover:border-ink hover:text-ink max-sm:col-span-full max-sm:mt-3">
            {open ? "접기" : "자격·근거"}<ChevronDown aria-hidden="true" size={13} className={cn("transition-transform motion-reduce:transition-none", open && "rotate-180")} />
          </button>
        )}
      </div>
      {children && (
        <div id={panelId} inert={!open} className={cn("x-wrap pl-10 max-sm:pl-0", open && "border-b border-rule bg-paper/60 pb-6 pt-4")} data-open={open}>
          <div className="-mx-1 px-1 pb-1">{children}</div>
        </div>
      )}
    </>
  );
}

export type QualLine = { state: "ok" | "none" | "warn" | "todo"; text: string };

/** 펼침 — 참가 자격(충족 ✓ 먹 600 > 제한 없음 회색 무표식 > 불충족 ✕ 주황) / 추천 근거 / 버튼 줄. */
export function SheetExpand({ quals, whys, actions }: { quals: QualLine[]; whys: ReactNode[]; actions?: ReactNode }) {
  return (
    <div className="grid grid-cols-[1fr_1.2fr] gap-7 max-sm:grid-cols-1 max-sm:gap-[18px]">
      {quals.length > 0 && (
        <div>
          <span className="t-k mb-2 block">참가 자격</span>
          <ul className="m-0 list-none p-0">
            {quals.map((q, i) => (
              <li key={i} className={cn("py-1 text-[14px] leading-[1.7]",
                q.state === "ok" && "font-semibold text-ink after:ml-1.5 after:content-['✓']",
                q.state === "none" && "text-ink-mute",
                q.state === "warn" && "text-ink after:ml-1.5 after:font-bold after:text-orange-ink after:content-['✕']",
                q.state === "todo" && "text-ink-mute")}>{q.text}</li>
            ))}
          </ul>
        </div>
      )}
      {whys.length > 0 && (
        <div>
          <span className="t-k mb-2 block">추천 근거</span>
          <ul className="m-0 list-none p-0">{whys.map((w, i) => <li key={i} className="py-1 text-[14px] leading-[1.7] text-ink-body">{w}</li>)}</ul>
        </div>
      )}
      {actions && <div className="col-span-full flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** 흐림 묶음 — 게이트 뒤 6건째부터. 글자는 읽히지 않되 존재는 보인다. inert 로 포커스·클릭·AT 전부 차단(게이트 우회 방지). */
export function SheetFade({ children, off = false }: { children: ReactNode; off?: boolean }) {
  return <div className={cn(!off && "[&>*]:opacity-[.32] [&>*]:blur-[1.5px]")} inert={!off}>{children}</div>;
}
