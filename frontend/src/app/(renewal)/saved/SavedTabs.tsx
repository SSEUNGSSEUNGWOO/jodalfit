// frontend/src/app/(renewal)/saved/SavedTabs.tsx
"use client";

import { useState, type ReactNode } from "react";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "n", label: "공고" },
  { id: "c", label: "저장한 회사" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function SavedTabs({ counts, notices, companies }: { counts: Record<TabId, number>; notices: ReactNode; companies: ReactNode }) {
  const [tab, setTab] = useState<TabId>("n");
  return (
    <>
      <PageHead title="검토함" className="pb-0">
        <div role="tablist" aria-label="검토함" className="mt-3.5 flex gap-6 text-[15px] max-sm:gap-[18px] max-sm:text-[14px]">
          {TABS.map((t) => {
            const on = tab === t.id;
            return (
              <button key={t.id} type="button" role="tab" id={`tab-${t.id}`} aria-selected={on} aria-controls={`pane-${t.id}`} onClick={() => setTab(t.id)}
                className={cn("-mb-px cursor-pointer border-b-2 border-transparent pb-3 text-ink-g", on && "border-ink font-[650] text-ink")}>
                {t.label}
                <small className="ml-1.5 text-[13.5px] font-[450] text-ink-mute">{counts[t.id]}</small>
              </button>
            );
          })}
        </div>
      </PageHead>
      <Panel className="mt-[22px] pt-1.5">
        <div role="tabpanel" id="pane-n" aria-labelledby="tab-n" hidden={tab !== "n"}>{notices}</div>
        <div role="tabpanel" id="pane-c" aria-labelledby="tab-c" hidden={tab !== "c"}>{companies}</div>
      </Panel>
    </>
  );
}
