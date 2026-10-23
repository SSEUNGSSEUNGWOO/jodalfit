// frontend/src/lib/why.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { whyLines, qualLines } from "./why.ts";

test("whyLines: 시안 gen_flow.why_lines 문장, vector 는 마지막", () => {
  const out = whyLines(
    [
      { key: "vector", label: "유사도 73%", points: 73 },
      { key: "institution", label: "재출현 기관", points: 12, instt: "경기도 평택시 상하수도사업소" },
      { key: "region", label: "지역 매칭", points: 9, rgn: "경상남도" },
      { key: "industry_tokens", label: "업종·물품 일치", points: 6, matched: ["공공하수도", "관리대행", "x", "y"] },
      { key: "budget", label: "예산대 매칭", points: 2, ratio: 1.08 },
      { key: "budget_mismatch", label: "예산대 괴리", points: -2, ratio: 12.5 },
      { key: "instt_closed", label: "고정 거래처 경향", points: -3, repeat_ratio: 0.62 },
    ],
    "경기도 평택시 상하수도사업소",
  );
  assert.deepEqual(out, [
    "경기도 평택시 상하수도사업소 — 과거 거래 이력 있음",
    "공고의 지역 제한이 본사 소재지 경상남도와 일치",
    "등록업종 표현이 허용업종과 중복 — 공공하수도, 관리대행, x",
    "추정가가 회사 평균 수주가의 1.08배 — 유사한 규모",
    "추정가가 회사 평균 수주가의 12.5배 — 규모 차이 큼",
    "해당 기관 최근 낙찰의 62%를 같은 회사가 수주",
    "공고 내용과 회사 업종 설명 유사도 73%",
  ]);
});

test("qualLines: reasons 를 세 상태로, 규모 줄은 항상 끝에", () => {
  const out = qualLines({ passed: true, unverified: false, reasons: ["면허 제한 없음", "지역 자격 충족"], failures: [] });
  assert.deepEqual(out, [
    { state: "none", text: "면허 — 제한 없음" },
    { state: "ok", text: "지역 — 자격 충족" },
    { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" },
  ]);
  assert.deepEqual(qualLines(undefined), [{ state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" }]);
  assert.deepEqual(
    qualLines({ passed: false, unverified: false, reasons: ["지역 제한 없음"], failures: ["면허 미충족(a, b)"] }),
    [
      { state: "none", text: "지역 — 제한 없음" },
      { state: "warn", text: "면허 — 미충족(a, b)" },
      { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" },
    ],
  );
});
