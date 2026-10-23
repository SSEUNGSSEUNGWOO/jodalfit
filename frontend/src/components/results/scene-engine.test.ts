// D-2 점 격자의 기하 불변식 — DOM 없이 순수 함수만 검사한다.
// node --experimental-strip-types --test src/components/results/scene-engine.test.ts
import assert from "node:assert/strict";
import test from "node:test";
import { SCENE, blockArea, geom, layout } from "./scene-engine.ts";

// 운영 실측값(2026-10-23): 지금 입찰 가능 8,225 → 후보 200 → 자격 통과 85 → 추천 20
const REAL = [8225, 200, 85, 20] as const;
// 데스크톱 1120×392 를 dpr 2 로 그린 캔버스
const WD = 2240;
const HD = 784;

test("네 칸이 다 들어간다", () => {
  const l = layout(REAL, WD, HD);
  assert.ok(l, "배치를 못 잡았다");
  assert.equal(l.shp.length, 4);
  assert.equal(l.gx.length, 3, "관문은 셋");
  for (const [c, r] of l.shp) assert.ok(c > 0 && r > 0, String(l.shp));
});

test("점유 면적이 건수에 비례한다 — D-2 의 주장", () => {
  const l = layout(REAL, WD, HD)!;
  const a0 = blockArea(l, 0);
  const n0 = REAL[0];
  for (let i = 1; i < 4; i++) {
    const areaRatio = blockArea(l, i) / a0;
    const cntRatio = REAL[i] / n0;
    // 칸을 격자로 채우면 낭비가 생긴다 — 10% 안이면 "면적이 건수"로 읽힌다.
    const err = Math.abs(areaRatio - cntRatio) / cntRatio;
    assert.ok(err < 0.1, `칸 ${i}: 면적비 ${areaRatio.toExponential(3)} vs 건수비 ${cntRatio.toExponential(3)}`);
  }
});

test("모든 칸이 같은 pitch 를 쓴다", () => {
  // 같은 pitch 가 아니면 면적 비례가 깨진다 — layout 이 pitch 를 하나만 돌려주는 것으로 보장된다.
  const l = layout(REAL, WD, HD)!;
  assert.ok(l.p > 0 && SCENE.PITCHES.includes(l.p as (typeof SCENE.PITCHES)[number]), String(l.p));
});

test("관문은 덩어리 사이에 있다 — 덩어리를 가로지르지 않는다", () => {
  const l = layout(REAL, WD, HD)!;
  for (let k = 0; k < 3; k++) {
    const rightEdge = l.cxs[k] + ((l.shp[k][0] - 1) * l.p) / 2;
    const leftEdge = l.cxs[k + 1] - ((l.shp[k + 1][0] - 1) * l.p) / 2;
    assert.ok(rightEdge < l.gx[k] && l.gx[k] < leftEdge, `관문 ${k} 가 덩어리와 겹친다`);
  }
});

test("마지막 칸은 눈으로 셀 수 있다", () => {
  const l = layout(REAL, WD, HD)!;
  // 20건이 한 줄로 서야 표 행으로 읽힌다. 열이 너무 많으면 덩어리로 보인다.
  assert.ok(l.shp[3][0] <= 6, `마지막 칸 열이 ${l.shp[3][0]} — 세기 어렵다`);
});

test("390px 모바일에서도 배치가 잡힌다", () => {
  // 390 × dpr 3 = 1170, 머리 높이 220 × 3 = 660
  const l = layout(REAL, 1170, 660);
  assert.ok(l, "390px 에서 배치 실패 — 캔버스가 빈다");
  assert.ok(l.p >= 1, `pitch ${l.p} 는 점이 사라진다`);
});

test("숫자가 오기 전에도 그릴 점이 있다 — 0건은 그대로 0", () => {
  const g = geom([-1, -1, -1, -1]);
  assert.ok(
    g.every((n) => n > 0),
    String(g),
  );
  assert.ok(layout(g, WD, HD), "기본값으로도 덩어리가 보여야 한다");
  assert.deepEqual(geom([8225, 200, 0, 0]), [8225, 200, 0, 0]); // 아는 0 은 지어내지 않는다
});

test("0건 칸은 빈 칸으로 둔다", () => {
  const l = layout([8225, 200, 0, 0], WD, HD);
  assert.ok(l);
  assert.deepEqual(l.shp[2], [0, 0]);
  assert.equal(blockArea(l, 3), 0);
});

test("탈락 이유 캡션은 캔버스 안에 있다", () => {
  assert.ok(SCENE.RSN_Y + 20 <= SCENE.H, String(SCENE.RSN_Y));
});
