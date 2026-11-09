"use client";

import posthog from "posthog-js";
import { getSessionId } from "./analytics-session";

export type AnalyticsEvent =
  | "search_submit"
  | "notice_click"
  | "notice_save"
  | "notice_save_intent"
  | "results_view"
  | "signup_view"
  | "g2b_outbound"
  | "result_helpful"    // 결과 화면 "도움이 됐습니까" (helpful 0/1, with_note 0/1) — DB 는 /events/helpful
  | "company_save"      // 회사 저장 (from welcome|saved|consent|star, suggested 1 = 방금 조회한 회사를 체크로 저장)
  | "consent_view"      // 소셜 가입 마무리 화면 노출 (suggested 0/1) — company_save(from consent) 와 나눠 저장 전환율(2026-11-09)
  | "welcome_view"      // 가입 확인 직후 우리 회사 저장 화면 노출 (suggested 0/1) — company_save(from welcome) 와 나눠 저장 전환율
  | "social_login_click"; // 소셜 로그인 버튼 (provider google, from login|signup) — 성공은 세션으로 안다

/** PostHog 미설정(키 없음)이면 조용히 무시한다. */
export function track(event: AnalyticsEvent, props?: Record<string, string | number | null | undefined>): void {
  if (!posthog.__loaded) return;
  if (typeof window === "undefined" || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)
      || /bot|crawl|spider|headless|meta-externalagent/i.test(navigator.userAgent)) return;
  posthog.capture(event, { ...props, jf_session_id: getSessionId() });
}
