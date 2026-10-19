import { NextResponse, type NextRequest } from "next/server";
import type { EmailOtpType } from "@supabase/supabase-js";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/safe-next";

/** 메일 링크 — token_hash 를 세션으로 바꾸고 next 로. 실패는 /login?error=link. recovery 는 /reset/new 로 강제. */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const token_hash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type") as EmailOtpType | null;
  const next = type === "recovery" ? "/reset/new" : safeNext(url.searchParams.get("next"));
  if (!token_hash || !type) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return NextResponse.redirect(new URL("/login?error=link", url.origin));
  }
  const supabase = await getServerSupabase({ strict: true });
  const { error } = await supabase.auth.verifyOtp({ token_hash, type });
  if (error) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  const res = NextResponse.redirect(new URL(next, url.origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
