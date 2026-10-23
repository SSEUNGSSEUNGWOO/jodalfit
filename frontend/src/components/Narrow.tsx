// frontend/src/components/Narrow.tsx
import type { ReactNode } from "react";
import { Panel } from "@/components/Panel";

/** 로그인·가입·재설정의 좁은 판 — 520px, 제목 28. 머리말(lead) 없음(문구 결정: 미사여구 제거). */
export function Narrow({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto mt-12 max-w-[520px] max-sm:mt-5">
      <h1 className="m-0 mb-3 text-[28px] font-semibold tracking-[-0.03em] text-ink max-sm:text-[22px]">{title}</h1>
      <Panel className="px-7 pb-7 pt-[26px] max-sm:px-4 max-sm:pb-[22px] max-sm:pt-5">{children}</Panel>
    </div>
  );
}
