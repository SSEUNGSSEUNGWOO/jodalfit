// frontend/src/proxy.ts
import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { SESSION_COOKIE_OPTIONS } from "@/lib/supabase/cookie-options";

let warned = false;

/** 매 요청 세션 토큰 갱신(만료된 access token 을 refresh 해 쿠키에 다시 쓴다). 보호 경로 리다이렉트는 하지 않는다 — 비로그인 /saved 는 안내 판(시안). */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  // 키 미설정이면 세션 갱신 건너뜀 — 02 Task 2 전 로컬
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (process.env.NODE_ENV === "production") throw new Error("NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
    if (!warned) { warned = true; console.warn("[proxy] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정 — 세션 갱신 건너뜀"); }
    return response;
  }
  const supabase = createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookieOptions: SESSION_COOKIE_OPTIONS,
    cookies: {
      getAll() { return request.cookies.getAll(); },
      setAll(cookiesToSet, headers?: Record<string, string>) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        Object.entries(headers ?? {}).forEach(([k, v]) => response.headers.set(k, v));   // 세션 쿠키 실린 응답은 캐시 금지
      },
    },
  });
  await supabase.auth.getUser();   // 갱신 트리거. 반환값은 안 쓴다
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg|opengraph-image|sitemap.xml|robots.txt|api/|.*\\.(?:png|jpg|svg|webp|txt)$).*)"],
};
