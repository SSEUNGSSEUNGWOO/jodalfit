// frontend/src/components/SaveCompanyForm.tsx
// 우리 회사 저장 폼 — 입구 검색창(회사 모드 고정)에서 고른 이름을 /api/saved/companies 로 보내 saved_companies 에 넣는다.
// 자리: 가입 확인 직후 /welcome(저장 회사 0곳) 과 검토함 회사 탭의 빈 상태. 주간 메일이 "저장한 회사" 기준이라 여기가 메일의 입구다(2026-10-28).
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SearchSuggest } from "@/components/entry/SearchSuggest";
import { track } from "@/lib/analytics";

type Status = { k: "idle" } | { k: "busy"; nm: string } | { k: "notfound"; nm: string } | { k: "error" };

export function SaveCompanyForm({ next, from }: {
  next?: string; // 저장 뒤 갈 곳. 없으면 그 자리에서 다시 그린다(검토함 빈 상태 → 행이 나타난다)
  from: "welcome" | "saved";
}) {
  const router = useRouter();
  const [st, setSt] = useState<Status>({ k: "idle" });

  async function pick(nm: string) {
    if (st.k === "busy") return;
    setSt({ k: "busy", nm });
    try {
      const r = await fetch("/api/saved/companies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nm }) });
      if (r.status === 404) { setSt({ k: "notfound", nm }); return; }
      if (!r.ok) { setSt({ k: "error" }); return; }
      track("company_save", { from });
      if (next) router.push(next); else { setSt({ k: "idle" }); router.refresh(); }
    } catch { setSt({ k: "error" }); }
  }

  return (
    <div data-save-company data-state={st.k}>
      <SearchSuggest lock="company" placeholder="우리 회사 이름 또는 사업자번호" compact onPick={pick} autoFocus={from === "welcome"} />
      {st.k === "busy" && <p className="m-0 mt-2.5 text-[13.5px] text-ink-g" aria-live="polite">{st.nm} 저장 중</p>}
      {st.k === "notfound" && <p role="alert" className="m-0 mt-2.5 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">&quot;{st.nm}&quot;은 조달핏에 없는 회사입니다. 목록에 뜨는 이름으로 고릅니다. 나라장터에 등록된 회사면 다음 시간부터 검색됩니다.</p>}
      {st.k === "error" && <p role="alert" className="m-0 mt-2.5 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">저장하지 못했습니다. 잠시 후 다시</p>}
    </div>
  );
}
