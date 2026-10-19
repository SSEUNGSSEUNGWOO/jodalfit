import { test } from "node:test";
import assert from "node:assert/strict";
import { safeNext } from "./safe-next.ts";

test("safeNext — 상대 경로만 통과", () => {
  assert.equal(safeNext("/saved"), "/saved");
  assert.equal(safeNext("/recommendations?company=%ED%95%9C%EC%A2%85&mode=company"), "/recommendations?company=%ED%95%9C%EC%A2%85&mode=company");
  assert.equal(safeNext("/companies/1248177731#top"), "/companies/1248177731#top");
});

test("safeNext — 밖으로 나가는 것은 전부 기본값", () => {
  assert.equal(safeNext("https://evil.example/x"), "/recommendations");
  assert.equal(safeNext("//evil.example"), "/recommendations");
  assert.equal(safeNext("/\\evil.example"), "/recommendations");
  assert.equal(safeNext("javascript:alert(1)"), "/recommendations");
  assert.equal(safeNext("saved"), "/recommendations");
  assert.equal(safeNext(""), "/recommendations");
  assert.equal(safeNext(null), "/recommendations");
  assert.equal(safeNext(undefined, "/"), "/");
});

test("safeNext — 로그인·가입 페이지로 되돌아가지 않는다", () => {
  assert.equal(safeNext("/login?next=/saved"), "/recommendations");
  assert.equal(safeNext("/signup"), "/recommendations");
  assert.equal(safeNext("/auth/confirm?x=1"), "/recommendations");
});
