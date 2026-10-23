// frontend/src/lib/why.ts
// 추천 근거 문장과 참가 자격 줄 — 시안 gen_flow.py::why_lines / qual_lines 와 같은 말. 순수 함수, node --test.
import type { QualLine } from "@/components/Sheet";
import type { ScoreSignal } from "@/types/recommendations";

export type Qualification = { passed: boolean; unverified: boolean; reasons: string[]; failures: string[] };

export function whyLines(breakdown: ScoreSignal[] | undefined, org: string): string[] {
  const out: string[] = [];
  let vector: string | null = null;
  for (const b of breakdown ?? []) {
    switch (b.key) {
      case "institution": out.push(`${org} — 과거 거래 이력 있음`); break;
      case "region": out.push(`공고의 지역 제한이 본사 소재지 ${String(b.rgn ?? "")}와 일치`); break;
      case "industry_tokens": out.push(`등록업종 표현이 허용업종과 중복 — ${((b.matched as string[] | undefined) ?? []).slice(0, 3).join(", ")}`); break;
      case "budget": out.push(`추정가가 회사 평균 수주가의 ${String(b.ratio)}배 — 유사한 규모`); break;
      case "budget_mismatch": out.push(`추정가가 회사 평균 수주가의 ${String(b.ratio)}배 — 규모 차이 큼`); break;
      case "instt_closed": out.push(`해당 기관 최근 낙찰의 ${Math.round(Number(b.repeat_ratio ?? 0) * 100)}%를 같은 회사가 수주`); break;
      case "vector": vector = `공고 내용과 회사 업종 설명 ${b.label}`; break;
      default: break; // peer_institution·deadline_urgent·qual_unverified 는 칩으로만(시안과 같음)
    }
  }
  if (vector) out.push(vector);
  return out;
}

const SIZE_LINE: QualLine = { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" };

export function qualLines(q: Qualification | undefined): QualLine[] {
  const fails = new Set(q?.failures ?? []);
  // reasons·failures 는 상호 배타 — 미충족은 failures 에만 온다
  const lines: QualLine[] = [...(q?.reasons ?? []), ...(q?.failures ?? [])].map((t) => ({
    state: fails.has(t) ? "warn" : t.includes("제한 없음") ? "none" : "ok",
    text: t.replace(/^면허 /, "면허 — ").replace(/^지역 /, "지역 — "),
  }));
  return [...lines, SIZE_LINE];
}
