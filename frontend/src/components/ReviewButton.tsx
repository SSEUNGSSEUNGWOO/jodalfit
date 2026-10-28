// frontend/src/components/ReviewButton.tsx
// 검토 / 검토함 — reviewed_notices 에 브라우저 클라이언트로 직접 insert/delete (RLS). 비로그인이면 로그인 링크.
// via = 어느 회사 결과에서 눌렀는지(bizrno_norm), why = 그 행의 근거 칩(strongestWhy) — 검토함 둘째 줄에 그대로 나온다.
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Btn } from "@/components/Btn";
import { track } from "@/lib/analytics";
import { emitNoticeEvent } from "@/lib/events";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function ReviewButton({ no, ord = "000", via = null, why = null, reviewed, loggedIn, onChange, className, next: returnTo, rank, score, algorithm, label = "검토", activeLabel = "검토함" }: {
  no: string; ord?: string; via?: string | null; why?: string | null; reviewed: boolean; loggedIn: boolean;
  onChange?: (reviewed: boolean) => void; className?: string; next?: string;
  rank?: number; score?: number; algorithm?: string; label?: string; activeLabel?: string;
}) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [on, setOn] = useState(reviewed);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();
  const [error, setError] = useState(false);
  const intent = () => track("notice_save_intent", { bid_ntce_no: no, logged_in: loggedIn ? 1 : 0, rank_position: rank });

  if (!loggedIn) {
    return <Btn variant="review" href={`/login?next=${encodeURIComponent(returnTo ?? pathname)}`} onClick={intent} className={className} data-review="guest">{label}</Btn>;
  }

  async function toggle() {
    if (busy) return;
    const next = !on;
    if (next) intent();
    setError(false);
    setBusy(true);
    try {
      const sb = getBrowserSupabase();
      const { error } = next
        ? await sb.from("reviewed_notices").insert({ bid_ntce_no: no, bid_ntce_ord: ord, via_bizrno_norm: via, why: why?.slice(0, 60) ?? null }) // why 는 DB check 60자
        : await sb.from("reviewed_notices").delete().eq("bid_ntce_no", no).eq("bid_ntce_ord", ord);
      if (error && error.code !== "23505") { setError(true); return; }
      setOn(next);
      onChange?.(next);
      if (next && !error) emitNoticeEvent({ event_type: "save", bid_ntce_no: no, bid_ntce_ord: ord, target_bizrno: via, rank_position: rank, score, algorithm_version: algorithm });
      start(() => router.refresh());
    } catch { setError(true); }
    finally { setBusy(false); }
  }

  return (
    <Btn variant="review" on={on} onClick={toggle} disabled={busy} aria-busy={busy} aria-pressed={on} className={className} data-review={on ? "on" : "off"}>
      {busy ? "처리 중" : error ? "다시 시도" : on ? activeLabel : label}
    </Btn>
  );
}
