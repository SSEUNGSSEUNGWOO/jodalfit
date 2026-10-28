import assert from "node:assert/strict";
import test from "node:test";
import { countConversions, type ConversionEvent } from "./admin-conversion.ts";

const event = (session: string, name: string, minute: number, loggedIn: boolean | null = null): ConversionEvent => ({ session, event: name, at: new Date(Date.UTC(2026, 9, 28, 0, minute)).toISOString(), loggedIn });

test("전환은 횟수가 아닌 탭 세션 수이며 직접 저장도 센다", () => {
  const result = countConversions([
    event("a", "results_view", 1), event("a", "notice_click", 2), event("a", "notice_click", 3),
    event("a", "notice_save_intent", 4, true), event("a", "notice_save", 5), event("a", "notice_save", 6),
    event("b", "results_view", 1), event("b", "notice_save_intent", 2, true), event("b", "notice_save", 3),
  ].reverse(), 0);
  assert.deepEqual(result, { results: 2, opened: 1, intent: 2, saved: 2, guestIntent: 0, signup: 0 });
});

test("이전 클릭·실패한 저장·직접 가입 방문을 전환으로 세지 않는다", () => {
  const result = countConversions([
    event("a", "notice_click", 0), event("a", "notice_save", 1), event("a", "results_view", 2),
    event("a", "signup_view", 3), event("a", "notice_save_intent", 4, false),
    event("b", "signup_view", 1), event("", "results_view", 1),
  ], 0);
  assert.deepEqual(result, { results: 1, opened: 0, intent: 1, saved: 0, guestIntent: 1, signup: 0 });
});

test("비로그인 저장 시도 이후 가입 진입만 세고 날짜별 결과 코호트를 구분한다", () => {
  const events = [event("a", "results_view", 1), event("a", "notice_save_intent", 2, false), event("a", "signup_view", 3),
    event("b", "results_view", 4), event("b", "notice_save_intent", 5, true), event("b", "signup_view", 6)];
  assert.equal(countConversions(events, 0).signup, 1);
  const today = countConversions(events, Date.parse(event("x", "results_view", 4).at));
  assert.deepEqual(today, { results: 1, opened: 0, intent: 1, saved: 0, guestIntent: 0, signup: 0 });
});
