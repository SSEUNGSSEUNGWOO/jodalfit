// frontend/src/lib/supabase/server.ts
import "server-only";
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

/**
 * 서버 컴포넌트·라우트 핸들러용(anon 키 + 요청 쿠키). 사용자 세션으로 RLS 테이블을 읽고 쓴다.
 * 공개 데이터 SSR 은 기존 `lib/supabase-server.ts`(service_role) 그대로 — 둘을 섞지 않는다.
 * 서버 컴포넌트에서는 setAll 이 실패할 수 있다(읽기 전용 렌더) — proxy.ts 가 갱신을 맡으므로 삼킨다.
 */
export async function getServerSupabase() {
  const store = await cookies();
  return createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookies: {
      getAll() { return store.getAll(); },
      setAll(cookiesToSet) {
        try { cookiesToSet.forEach(({ name, value, options }) => store.set(name, value, options)); } catch { /* 서버 컴포넌트 렌더 중 — proxy 가 갱신 */ }
      },
    },
  });
}
