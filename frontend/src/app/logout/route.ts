import { NextResponse, type NextRequest } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";

let warned = false;

/** 로그아웃 — 쿠키 세션 제거 후 홈. Nav 가 <a href="/logout"> 로 온다(프리페치 안 되게 Link 가 아님). */
export async function GET(req: NextRequest) {
  if (req.headers.get("sec-fetch-site") && req.headers.get("sec-fetch-site") !== "same-origin") return NextResponse.redirect(new URL("/", new URL(req.url).origin));
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    const supabase = await getServerSupabase({ strict: true });
    await supabase.auth.signOut();
  } else if (!warned) {
    warned = true; console.warn("[logout] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
  }
  const res = NextResponse.redirect(new URL("/?logout=1", new URL(req.url).origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
