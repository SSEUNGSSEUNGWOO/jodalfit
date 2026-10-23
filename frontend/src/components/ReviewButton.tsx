// frontend/src/components/ReviewButton.tsx
// 검토 / 검토함 — reviewed_notices 에 브라우저 클라이언트로 직접 insert/delete (RLS). 비로그인이면 로그인 링크.
// via = 어느 회사 결과에서 눌렀는지(bizrno_norm), why = 그 행의 근거 칩(strongestWhy) — 검토함 둘째 줄에 그대로 나온다.
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Btn } from "@/components/Btn";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function ReviewButton({ no, ord = "000", via = null, why = null, reviewed, loggedIn, onChange, className }: {
  no: string; ord?: string; via?: string | null; why?: string | null; reviewed: boolean; loggedIn: boolean;
  onChange?: (reviewed: boolean) => void; className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [on, setOn] = useState(reviewed);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();

  if (!loggedIn) {
    return <Btn variant="review" href={`/login?next=${encodeURIComponent(pathname)}`} className={className} data-review="guest">검토</Btn>;
  }

  async function toggle() {
    if (busy) return;
    const next = !on;
    setOn(next);
    onChange?.(next);
    setBusy(true);
    const sb = getBrowserSupabase();
    const { error } = next
      ? await sb.from("reviewed_notices").insert({ bid_ntce_no: no, bid_ntce_ord: ord, via_bizrno_norm: via, why })
      : await sb.from("reviewed_notices").delete().eq("bid_ntce_no", no).eq("bid_ntce_ord", ord);
    setBusy(false);
    if (error && error.code !== "23505") { setOn(!next); onChange?.(!next); return; }
    start(() => router.refresh());
  }

  return (
    <Btn variant="review" on={on} onClick={toggle} aria-pressed={on} className={className} data-review={on ? "on" : "off"}>
      {on ? "검토함" : "검토"}
    </Btn>
  );
}
