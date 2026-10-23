import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

/** 흰 판 — 14px(390: 12px), 헤어라인. 결과·회사·검토함·로그인이 전부 이 판 하나를 반복한다. */
export function Panel({ children, className, ...rest }: { children: ReactNode; className?: string } & ComponentProps<"section">) {
  return (
    <section className={cn("rounded-[14px] max-sm:rounded-[12px] border border-hair bg-panel px-7 pb-7 pt-1.5 max-sm:px-4 max-sm:pb-5 max-sm:pt-0", className)} {...rest}>
      {children}
    </section>
  );
}

/** 판 안 제목 줄 — 제목 16 + 작은 글 / 오른쪽 요약(· 구분). 아래 먹 괘선. */
export function PanelHead({ title, small, summary, className }: {
  title: ReactNode; small?: ReactNode; summary?: ReactNode[]; className?: string;
}) {
  return (
    <div className={cn("rule-ink flex flex-wrap items-baseline justify-between gap-5 pt-[22px] pb-3", className)}>
      <h2 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-ink">
        {title}{small && <small className="ml-2 text-[13.5px] font-normal text-ink-dim">{small}</small>}
      </h2>
      {summary && summary.length > 0 && (
        <div className="text-[13.5px] text-ink-g [&_b]:font-semibold [&_b]:text-ink [&>span+span]:before:mx-2 [&>span+span]:before:text-[#c9c9c4] [&>span+span]:before:content-['·']">
          {summary.map((s, i) => <span key={i}>{s}</span>)}
        </div>
      )}
    </div>
  );
}
