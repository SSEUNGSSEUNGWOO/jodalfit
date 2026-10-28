import { NextResponse, type NextRequest } from "next/server";
import type { EmailOtpType } from "@supabase/supabase-js";
import { getServerSupabase } from "@/lib/supabase/server";
import { afterAuthDestination } from "@/lib/after-auth";
import { safeNext } from "@/lib/safe-next";

let warned = false;

/** 메일 링크 — token_hash 를 세션으로 바꾸고 next 로. 실패는 /login?error=link. recovery 는 /reset/new 로 강제. */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const token_hash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type") as EmailOtpType | null;
  const next = type === "recovery" ? "/reset/new" : safeNext(url.searchParams.get("next"));
  if (!token_hash || !type) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (!warned) { warned = true; console.warn("[auth/confirm] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정"); }
    return NextResponse.redirect(new URL("/login?error=link", url.origin));
  }
  const supabase = await getServerSupabase({ strict: true });
  const { error } = await supabase.auth.verifyOtp({ token_hash, type });
  if (error) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  // 가입 확인이면 저장 회사 0곳인 사람을 /welcome 으로(lib/after-auth, 2026-10-28). recovery 는 /reset/new 그대로.
  const dest = type === "recovery" ? next : await afterAuthDestination(supabase, next, { signup: type === "signup" || type === "email" });
  const res = NextResponse.redirect(new URL(dest, url.origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
