// frontend/src/lib/auth.ts
import "server-only";
import { cache } from "react";
import type { NavUser } from "@/components/Nav";
import { getServerSupabase } from "@/lib/supabase/server";

export type SessionUser = { id: string; email: string };

let warned = false;

/** 서버에서 현재 사용자. getUser 는 토큰을 서버에서 검증한다(getSession 은 쿠키를 믿는다 — 쓰지 않는다). */
export const getSessionUser = cache(async (): Promise<SessionUser | null> => {
  // 키 미설정이면 비로그인으로 — 02 Task 2 전 로컬
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (process.env.NODE_ENV === "production") throw new Error("NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
    if (!warned) { warned = true; console.warn("[auth] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정 — 비로그인으로 동작"); }
    return null;
  }
  const supabase = await getServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  return user?.email ? { id: user.id, email: user.email } : null;
});

/** Nav 가 받는 모양. 저장한 회사·검토 건수는 03 에서 채운다. */
export async function getNavUser(): Promise<NavUser | null> {
  const u = await getSessionUser();
  return u ? { email: u.email, savedCompanies: [], reviewedCount: 0 } : null;
}
