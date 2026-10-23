import test from "node:test";
import assert from "node:assert/strict";
import { companyStats, strongestWhy } from "./saved-stats.ts";

const today = new Date(2026, 9, 16); // 2026-10-16

test("companyStats: 마감 지난 것은 빼고, 7일 이내를 이번 주로, 가장 빠른 마감을 고른다", () => {
  const s = companyStats(["2026-10-20", "2026-11-25", "2026-10-10", null, "2026-10-23"], today);
  assert.deepEqual(s, { total: 3, week: 1, soonest: { days: 4, month: 10, day: 20 } });
});

test("companyStats: 결과가 없으면 0 과 null", () => {
  assert.deepEqual(companyStats([], today), { total: 0, week: 0, soonest: null });
});

test("strongestWhy: vector 를 빼고 양수 점수 중 최대의 label", () => {
  const w = strongestWhy([
    { key: "vector", label: "유사도 73%", points: 73 },
    { key: "region", label: "지역 매칭", points: 9 },
    { key: "institution", label: "재출현 기관", points: 12 },
    { key: "deadline_urgent", label: "마감 임박", points: -9 },
  ]);
  assert.equal(w, "재출현 기관");
});

test("strongestWhy: 양수 신호가 없으면 null", () => {
  assert.equal(strongestWhy([{ key: "vector", label: "유사도 50%", points: 50 }]), null);
  assert.equal(strongestWhy(undefined), null);
});
