import assert from "node:assert/strict";
import test from "node:test";
import { readAdminRows, summarizeMembers, summarizeSearches } from "./admin-summary.ts";

test("회원 집계는 기간 경계와 관리자·테스트 제외, 저장 회원 중복을 구분한다", () => {
  const from = Date.parse("2026-10-29T00:00:00+09:00"), until = from + 7 * 86400000;
  const user = (id: string, at: number, email = `${id}@example.com`) => ({ id, email, created_at: new Date(at).toISOString(), email_confirmed_at: id === "a" ? "confirmed" : null });
  const result = summarizeMembers([user("a", from), user("b", from - 1), user("c", until), user("owner", from, "OWNER@example.com"), user("test", from, "test@jodalfit.test")],
    [{ user_id: "a" }, { user_id: "a" }, { user_id: "owner" }], [{ user_id: "b" }, { user_id: "deleted" }], from, until, ["owner@example.com"]);
  assert.deepEqual(result, { total: 3, confirmed: 1, newMembers: 1, previousNewMembers: 1, companyUsers: 1, companies: 2, noticeUsers: 1, notices: 1, excluded: 2 });
});

test("완료 7일 검색은 오늘을 빼고 실패 유형을 나눈다", () => {
  const from = Date.parse("2026-10-29T00:00:00+09:00"), until = from + 7 * 86400000;
  const row = (at: number, has_error: boolean, error_msg: string | null) => ({ created_at: new Date(at).toISOString(), has_error, error_msg, query: null, mode: null });
  assert.deepEqual(summarizeSearches([row(from - 1, true, null), row(from, true, "회사를 찾을 수 없습니다"), row(from + 1, true, "등록업종 없음"), row(from + 2, true, null), row(from + 3, false, null), row(until, true, null)], from, until),
    { total: 4, problems: 3, missingCompany: 1, missingProfile: 1, other: 1 });
});

test("페이지 집계는 기본 상한을 넘겨 읽고 정확한 상한과 초과를 구분한다", async () => {
  for (const size of [0, 3, 4, 5]) {
    const source = Array.from({ length: size }, (_, i) => i);
    const result = await readAdminRows(async (a, b) => ({ data: source.slice(a, b + 1), error: null }), 2, 4);
    assert.deepEqual(result, { data: source.slice(0, 4), error: null, truncated: size > 4 });
  }
});

test("중간 조회 실패를 부분 합계나 0이라는 정상 결과로 반환하지 않는다", async () => {
  const result = await readAdminRows(async (from) => from === 0 ? { data: [1, 2], error: null } : { data: null, error: { message: "unavailable" } }, 2);
  assert.deepEqual(result, { data: [], error: "unavailable", truncated: false });
  const thrown = await readAdminRows(async () => { throw new Error("network"); });
  assert.ok(thrown.error);
});
