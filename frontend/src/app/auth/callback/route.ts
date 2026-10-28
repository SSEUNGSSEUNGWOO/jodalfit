// frontend/src/app/auth/callback/route.ts
// OAuth(구글) 콜백 — Supabase 가 ?code= 로 돌려보내면 세션으로 바꾸고 next 로(2026-10-28).
// 실패는 /login?error=oauth. 첫 소셜 가입은 동의가 비어 있어 lib/after-auth 가 /consent 로 보낸다(0064).
// 소셜 가입은 "가입"인지 "로그인"인지 구분할 신호가 없다 — created_at 이 1분 안이면 가입으로 본다(/welcome 안내 여부에만 쓴다).
import { NextResponse, type NextRequest } from "next/server";
import { afterAuthDestination } from "@/lib/after-auth";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/safe-next";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const next = safeNext(url.searchParams.get("next"));
  if (!code || !process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return NextResponse.redirect(new URL("/login?error=oauth", url.origin));
  }
  const supabase = await getServerSupabase({ strict: true });
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error || !data.user) return NextResponse.redirect(new URL("/login?error=oauth", url.origin));
  const signup = Date.now() - new Date(data.user.created_at).getTime() < 60_000;
  const dest = await afterAuthDestination(supabase, next, { signup });
  const res = NextResponse.redirect(new URL(dest, url.origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
