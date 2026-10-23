// 검토함 회사 행의 숫자와 근거 칩 — 시안 gen_saved.py:91-92 (n = 결과 수, wk = D-7 이내, d = 가장 빠른 마감),
// gen_results_v2.py::strongest (vector 제외, points > 0 중 최대) 와 같은 규칙. 순수 함수 — node --test.
import { dLeft } from "./format.ts";

export type DLeft = { days: number; month: number; day: number };
export type CompanyStats = { total: number; week: number; soonest: DLeft | null };

export function companyStats(clseDates: (string | null | undefined)[], today: Date = new Date()): CompanyStats {
  const ds = clseDates.map((d) => dLeft(d, today)).filter((x): x is DLeft => !!x && x.days >= 0);
  let soonest: DLeft | null = null;
  for (const x of ds) if (!soonest || x.days < soonest.days) soonest = x;
  return { total: ds.length, week: ds.filter((x) => x.days <= 7).length, soonest };
}

export type ScoreSignalLike = { key: string; label: string; points: number };

export function strongestWhy(breakdown: ScoreSignalLike[] | null | undefined): string | null {
  let best: ScoreSignalLike | null = null;
  for (const s of breakdown ?? []) {
    if (s.key === "vector" || s.points <= 0) continue;
    if (!best || s.points > best.points) best = s;
  }
  return best?.label ?? null;
}
