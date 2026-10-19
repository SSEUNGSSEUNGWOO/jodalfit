// frontend/src/lib/auth.ts
import "server-only";
import type { NavUser } from "@/components/Nav";
import { getServerSupabase } from "@/lib/supabase/server";

export type SessionUser = { id: string; email: string };

/** 서버에서 현재 사용자. getUser 는 토큰을 서버에서 검증한다(getSession 은 쿠키를 믿는다 — 쓰지 않는다). */
export async function getSessionUser(): Promise<SessionUser | null> {
  const supabase = await getServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  return user?.email ? { id: user.id, email: user.email } : null;
}

/** Nav 가 받는 모양. 저장한 회사·검토 건수는 03 에서 채운다. */
export async function getNavUser(): Promise<NavUser | null> {
  const u = await getSessionUser();
  return u ? { email: u.email, savedCompanies: [], reviewedCount: 0 } : null;
}
