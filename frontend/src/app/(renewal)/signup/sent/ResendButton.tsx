"use client";

import { useEffect, useState } from "react";
import { getBrowserSupabase } from "@/lib/supabase/browser";

/** 다시 보내기 — 60초 뒤 활성. signup 은 auth.resend, recovery 는 resetPasswordForEmail 재호출. */
export function ResendButton({ email, next, kind }: { email: string; next: string; kind: "signup" | "recovery" }) {
  const [left, setLeft] = useState(60); const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const [sentCount, setSentCount] = useState(0);
  useEffect(() => { if (left <= 0) return; const t = setTimeout(() => setLeft((s) => s - 1), 1000); return () => clearTimeout(t); }, [left]);
  async function resend() {
    setState("busy");
    const sb = getBrowserSupabase();
    const redirectTo = `${location.origin}/auth/confirm?next=${encodeURIComponent(kind === "recovery" ? "/reset/new" : next)}`;
    const { error } = kind === "signup" ? await sb.auth.resend({ type: "signup", email, options: { emailRedirectTo: redirectTo } }) : await sb.auth.resetPasswordForEmail(email, { redirectTo });
    if (!error) setSentCount((c) => c + 1);
    setState(error ? "error" : "idle"); setLeft(60);
  }
  if (left > 0) return <span className="text-ink-mute">{sentCount > 0 && <span className="text-ink-g">다시 보냈습니다 · </span>}다시 보내기 — {left}초 뒤</span>;
  return <button type="button" onClick={resend} disabled={state === "busy"} className="u-link text-ink">{state === "error" ? "다시 보내기(실패, 재시도)" : "다시 보내기"}</button>;
}
