"use client";

import posthog from "posthog-js";

export type AnalyticsEvent =
  | "search_submit"
  | "notice_click"
  | "notice_save"
  | "g2b_outbound"
  | "result_helpful";   // 결과 화면 "도움이 됐습니까" (helpful 0/1, with_note 0/1) — DB 는 /events/helpful

/** PostHog 미설정(키 없음)이면 조용히 무시한다. */
export function track(event: AnalyticsEvent, props?: Record<string, string | number | null | undefined>): void {
  if (!posthog.__loaded) return;
  posthog.capture(event, props);
}
