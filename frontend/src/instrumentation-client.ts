import * as Sentry from "@sentry/nextjs";
import posthog from "posthog-js";

// --- Sentry (DSN 비우면 비활성) ---
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0,
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,
});
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

// --- PostHog (키 비우면 비활성) ---
const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
if (key) {
  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com",
    defaults: "2026-08-30", // capture_pageview: history_change 포함
    persistence: "localStorage", // 쿠키 없음 → 동의 배너 불필요
    capture_pageleave: true,
  });

  // 나라장터 원문 클릭 — BidCard는 서버 컴포넌트라 onClick을 못 붙여서 문서 레벨에서 잡는다.
  document.addEventListener("click", (e) => {
    const a = (e.target as Element | null)?.closest<HTMLAnchorElement>('a[target="_blank"]');
    if (a && a.hostname.endsWith("g2b.go.kr")) {
      posthog.capture("g2b_outbound", { href: a.href });
    }
  });
}
