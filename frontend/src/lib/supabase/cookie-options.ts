// frontend/src/lib/supabase/cookie-options.ts
// 세션 쿠키 옵션 — browser/server/proxy 세 클라이언트가 같은 값을 쓴다(다르면 쿠키가 둘로 갈린다).
// @supabase/ssr 기본값(path=/, sameSite=lax, httpOnly=false)은 그대로 두고 운영에서 Secure 만 더한다.
// httpOnly 는 브라우저 클라이언트가 쿠키를 읽어야 해서 켤 수 없다(2026-10-26 보안 점검).
export const SESSION_COOKIE_OPTIONS = {
  secure: process.env.NODE_ENV === "production",
} as const;
