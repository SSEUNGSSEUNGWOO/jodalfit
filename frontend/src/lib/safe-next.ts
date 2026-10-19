/** 로그인·가입·확인 뒤 돌아갈 곳. 상대 경로(`/` 하나로 시작)만 허용 — 오픈 리다이렉트 방지(renewal-00 §3.2). */
const AUTH_PATHS = /^\/(login|signup|reset|auth\/|logout)/;

export function safeNext(raw: string | null | undefined, fallback = "/recommendations"): string {
  if (!raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return fallback;
  if (raw.includes("://") || /[\u0000-\u001f]/.test(raw)) return fallback;
  if (AUTH_PATHS.test(raw)) return fallback;
  return raw;
}
