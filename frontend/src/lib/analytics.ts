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
  | "company_save"      // 저장 폼(SaveCompanyForm)으로 회사 저장 (from welcome|saved) — ☆ 버튼 저장은 세지 않는다
  | "social_login_click"; // 소셜 로그인 버튼 (provider google, from login|signup) — 성공은 세션으로 안다

/** PostHog 미설정(키 없음)이면 조용히 무시한다. */
export function track(event: AnalyticsEvent, props?: Record<string, string | number | null | undefined>): void {
  if (!posthog.__loaded) return;
  if (typeof window === "undefined" || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)
      || /bot|crawl|spider|headless|meta-externalagent/i.test(navigator.userAgent)) return;
  posthog.capture(event, { ...props, jf_session_id: getSessionId() });
}
