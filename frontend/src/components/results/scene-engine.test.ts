// gen_flow.py --demo 의 기하 불변식 — DOM 없이 상수만 검사한다.
// node --experimental-strip-types --test src/components/results/scene-engine.test.ts
import assert from "node:assert/strict";
import test from "node:test";
import { SCENE, gaps, geom } from "./scene-engine.ts";

test("통로는 좁아진다", () => {
  const { HH } = SCENE;
  assert.ok(HH[0] > HH[1] && HH[1] > HH[2] && HH[2] > HH[3], String(HH));
});

test("캔버스 밖으로 새지 않는다", () => {
  const { CY, HH, FAN_SP, H } = SCENE;
  assert.ok(CY + HH[0] <= H && CY - HH[0] >= 0);
  assert.ok(CY + FAN_SP <= H && CY - FAN_SP >= 0);
  const { RSN_Y } = SCENE; // 탈락 이유 캡션은 통로 안, 캔버스 안
  assert.ok(CY - HH[0] < RSN_Y && RSN_Y < CY + HH[0] && RSN_Y + 20 <= H, String(RSN_Y));
});

test("간격이 '셀 수 없음 → 셀 수 있음'을 넘어간다", () => {
  const g = gaps([9374, 835, 372, 12]);
  assert.ok(g[0] < g[1] && g[1] < g[2] && g[2] < g[3], String(g));
  assert.ok(g[0] < 0.1, `덩어리로 안 보인다 ${g[0]}`);
  assert.ok(g[3] > 8, `마지막을 눈으로 셀 수 없다 ${g[3]}`);
});

test("숫자가 오기 전에도 그릴 선이 있다 — 0건은 그대로 0", () => {
  const g = geom([-1, -1, -1, -1]);
  assert.ok(g.every((n) => n > 0), String(g));
  assert.ok(gaps(g)[0] < 0.1, "기본값도 덩어리로 보여야 한다");
  assert.deepEqual(geom([9900, 845, 0, 0]), [9900, 845, 0, 0]); // 아는 0 은 지어내지 않는다
});
