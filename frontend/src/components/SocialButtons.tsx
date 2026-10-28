// frontend/src/components/SocialButtons.tsx
// 소셜 로그인 버튼 — 구글(Supabase 기본 공급자) + 네이버(Custom OAuth `custom:naver`, userinfo 는 /api/auth/naver/userinfo 중계), 2026-10-28. 로그인·가입 폼 위에 같은 모양으로.
// 구글 브랜드 규칙: 'G' 마크는 네 가지 색 원본 그대로, 문구 "Google로 계속". 버튼 자체는 사이트의 선 버튼(흰 판 + 헤어라인)이라 주황 면은 없다.
// 돌아오는 곳은 /auth/callback?next= — Supabase 대시보드 URL Configuration 의 Redirect URLs 에 사이트 주소(/**)가 있어야 한다.
"use client";

import { useState } from "react";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { track } from "@/lib/analytics";

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

/** 네이버 마크 — 브랜드 녹색 타일에 흰 N. 네이버 로그인 버튼 지침의 색(#03C75A)을 그대로 쓴다(구글 G 와 같은 이유 — 남의 브랜드는 남의 색). */
function NaverN() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <rect width="18" height="18" rx="3" fill="#03C75A" />
      <path fill="#fff" d="M10.3 4.5v4.6L7.7 4.5H4.9v9h2.8V8.9l2.6 4.6h2.8v-9z" />
    </svg>
  );
}

type Provider = "google" | "custom:naver";
// 네이버는 Supabase 대시보드에 custom:naver 공급자가 있어야 한다 — 설정 전엔 버튼을 숨긴다(Vercel 환경변수 NEXT_PUBLIC_NAVER_LOGIN=1).
const NAVER_ON = process.env.NEXT_PUBLIC_NAVER_LOGIN === "1";

export function SocialButtons({ next, from }: { next: string; from: "login" | "signup" }) {
  const [busy, setBusy] = useState<Provider | null>(null);
  const [err, setErr] = useState<Provider | null>(null);

  async function go(provider: Provider) {
    if (busy) return; setBusy(provider); setErr(null);
    track("social_login_click", { provider: provider.replace("custom:", ""), from });
    const { error } = await getBrowserSupabase().auth.signInWithOAuth({
      provider: provider as "google", // supabase-js 의 Provider 타입은 custom: 접두 문자열을 모른다 — 서버는 받는다(docs/guides/auth/custom-oauth-providers)
      options: { redirectTo: `${location.origin}/auth/callback?next=${encodeURIComponent(next)}` },
    });
    if (error) { setErr(provider); setBusy(null); } // 성공이면 공급자로 떠난다
  }

  const cls = "flex h-[46px] w-full cursor-pointer items-center justify-center gap-2.5 rounded-[8px] border border-field bg-panel text-[15px] font-semibold text-ink transition-colors duration-150 hover:border-orange disabled:cursor-default disabled:text-ink-off";
  return (
    <div data-social className="flex flex-col gap-2.5">
      <button type="button" onClick={() => go("google")} disabled={!!busy} data-social-google className={cls}>
        <GoogleG />{busy === "google" ? "Google로 이동 중" : "Google로 계속"}
      </button>
      {NAVER_ON && (
        <button type="button" onClick={() => go("custom:naver")} disabled={!!busy} data-social-naver className={cls}>
          <NaverN />{busy === "custom:naver" ? "네이버로 이동 중" : "네이버로 계속"}
        </button>
      )}
      {err && <p role="alert" className="border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err === "google" ? "Google" : "네이버"} 로그인을 시작하지 못했습니다. 잠시 후 다시</p>}
      <div className="my-[8px] flex items-center gap-3 text-[12px] text-ink-mute"><span className="h-px flex-1 bg-rule" />또는 이메일로<span className="h-px flex-1 bg-rule" /></div>
    </div>
  );
}
