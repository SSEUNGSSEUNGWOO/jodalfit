// frontend/src/components/StarCompany.tsx
// ☆ 회사 저장 / ★ 저장됨 — saved_companies 에 브라우저 클라이언트로 직접 insert/delete (RLS). 비로그인이면 로그인 링크.
// 시안(login-final 장면 5·README): ☆ 회색 → ★ 주황 테두리 "저장됨". 05 결과 머리·06 회사 머리가 이 부품을 PageHead aside 에 꽂는다.
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Btn } from "@/components/Btn";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

export function StarCompany({ bizrnoNorm, saved, loggedIn, className, next: returnTo }: { bizrnoNorm: string; saved: boolean; loggedIn: boolean; className?: string; next?: string }) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [on, setOn] = useState(saved);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();

  if (!loggedIn) {
    return (
      <Btn href={`/login?next=${encodeURIComponent(returnTo ?? pathname)}`} className={className} data-star="guest">
        <span className="mr-1 text-ink-mute">☆</span>회사 저장
      </Btn>
    );
  }

  async function toggle() {
    if (busy) return;
    const next = !on;
    setOn(next);
    setBusy(true);
    const sb = getBrowserSupabase();
    const { error } = next
      ? await sb.from("saved_companies").insert({ bizrno_norm: bizrnoNorm })
      : await sb.from("saved_companies").delete().eq("bizrno_norm", bizrnoNorm);
    setBusy(false);
    if (error && error.code !== "23505") { setOn(!next); return; } // 23505 = 이미 저장됨 → 성공으로 본다
    start(() => router.refresh()); // Nav ★ 목록·검토함 숫자 갱신
  }

  return (
    <Btn variant={on ? "review" : "line"} onClick={toggle} aria-pressed={on} className={className} data-star={on ? "on" : "off"}>
      <span className={cn("mr-1", on ? "text-orange-ink" : "text-ink-mute")}>{on ? "★" : "☆"}</span>
      {on ? "저장됨" : "회사 저장"}
    </Btn>
  );
}
