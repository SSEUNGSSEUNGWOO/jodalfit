import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * 머리 — 제목 32 + 제목 옆 작은 글(사업자번호 등), aside(다른 회사·☆)는 h1 밖 형제(접근성 — 제목 이름에 버튼 글자가 섞이지 않게) / 메타 줄(· 구분) / children(걸러낸 경로·탭) / 아래 먹 괘선 하나.
 * 바닥(paper) 위에 놓인다. 판 밖.
 */
export function PageHead({ title, small, aside, meta, children, className }: {
  title: ReactNode; small?: ReactNode; aside?: ReactNode; meta?: ReactNode[]; children?: ReactNode; className?: string;
}) {
  return (
    <div className={cn("rule-ink pt-[26px] pb-[18px]", className)}>
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h1 className="m-0 flex flex-wrap items-baseline gap-x-3 text-[32px] max-sm:text-[24px] font-semibold tracking-[-0.035em] leading-[1.2] text-ink">
          <span>{title}</span>
          {small && <small className="text-[13px] font-normal tracking-normal text-ink-mute">{small}</small>}
        </h1>
        {aside}
      </div>
      {meta && meta.length > 0 && (
        <div className="mt-1.5 text-[14px] text-ink-g [&>span+span]:before:mx-2 [&>span+span]:before:text-[#c9c9c4] [&>span+span]:before:content-['·']">
          {meta.map((m, i) => <span key={i}>{m}</span>)}
        </div>
      )}
      {children}
    </div>
  );
}
