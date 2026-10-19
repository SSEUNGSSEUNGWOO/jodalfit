import { test } from "node:test";
import assert from "node:assert/strict";
import { won, wonFull, dLeft, ymd, rgnBase } from "./format.ts";

test("won — 억·만 축약, 없으면 —", () => {
  assert.equal(won(5025454546), "50.3억");
  assert.equal(won(6000000000), "60억");       // .0억 은 억
  assert.equal(won(2000000), "200만");
  assert.equal(won(0), "—");
  assert.equal(won(null), "—");
  assert.equal(won(1), "—");
  assert.equal(won(9999), "—");
});

test("wonFull — 전액 원", () => {
  assert.equal(wonFull(6824573000), "6,824,573,000원");
  assert.equal(wonFull(null), "—");
  assert.equal(wonFull(1), "—");
});

test("dLeft — 오늘 기준 남은 일수와 날짜", () => {
  const today = new Date(2026, 9, 16);         // 2026-10-16
  assert.deepEqual(dLeft("2026-10-29", today), { days: 13, month: 10, day: 29 });
  assert.deepEqual(dLeft("2026-10-16T00:00:00+00:00", today), { days: 0, month: 10, day: 16 });
});

test("dLeft — 없거나 깨진 날짜는 null", () => {
  const today = new Date(2026, 9, 16);
  assert.equal(dLeft(null), null);
  assert.equal(dLeft("", today), null);
  assert.equal(dLeft("not-a-date", today), null);
});

test("ymd — 2026.10.16", () => {
  assert.equal(ymd("2026-10-16"), "2026.10.16");
  assert.equal(ymd("2026-10-16T02:19:35+00:00"), "2026.10.16");
  assert.equal(ymd(null), "—");
});

test("rgnBase — 기초자치단체까지, 일반구·동 제거", () => {
  assert.equal(rgnBase("경상남도 창원시 마산합포구"), "경상남도 창원시");
  assert.equal(rgnBase("부산광역시 동구"), "부산광역시 동구");
  assert.equal(rgnBase("경기도 성남시 분당구 정자동"), "경기도 성남시");
  assert.equal(rgnBase(null), "");
});
