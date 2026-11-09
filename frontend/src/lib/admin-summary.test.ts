import assert from "node:assert/strict";
import test from "node:test";
import { fallbackKeys, readAdminRows, searchKey, summarizeMembers, summarizeSearches } from "./admin-summary.ts";

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
    { total: 4, problems: 3, missingCompany: 1, missingProfile: 1, other: 1, fallback: 0 });
});

test("회사를 못 찾은 뒤 같은 방문자가 같은 질의를 2분 안에 키워드로 다시 남기면 '키워드 결과로 이어짐'이다", () => {
  const from = Date.parse("2026-10-29T00:00:00+09:00"), until = from + 7 * 86400000;
  const row = (at: number, mode: string, has_error: boolean, query: string, ip_hash = "aaaa") => ({ created_at: new Date(at).toISOString(), has_error, error_msg: has_error ? "회사를 찾을 수 없습니다" : null, query, mode, ip_hash });
  const rows = [
    row(from, "company", true, "토목설계업체"), row(from + 30_000, "keywords", false, "토목설계업체"),          // 이어짐
    row(from + 60_000, "company", true, "이노클"),                                                              // 후속 없음
    row(from + 120_000, "company", true, "교복"), row(from + 120_000 + 121_000, "keywords", false, "교복"),      // 2분 초과
    row(from + 300_000, "company", true, "천마", "bbbb"), row(from + 310_000, "keywords", false, "천마", "cccc"), // 다른 방문자
    row(until - 1000, "company", true, "구내식당"), row(until + 1000, "keywords", false, "구내식당"),             // 후속이 기간 밖(오늘)이어도 센다
  ];
  assert.deepEqual([...fallbackKeys(rows)], [searchKey(rows[0]), searchKey(rows[7])]);
  assert.deepEqual(summarizeSearches(rows, from, until), { total: 8, problems: 5, missingCompany: 5, missingProfile: 0, other: 0, fallback: 2 });
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
