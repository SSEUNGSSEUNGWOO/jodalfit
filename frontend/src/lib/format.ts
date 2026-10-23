/** 시안 생성기 gen_results.py::won/dleft, gen_company.py::ymd, gen_split.py::rgn_base 와 같은 규칙. */

export function won(v: number | string | null | undefined): string {
  const n = typeof v === "string" ? Number(v) : v;
  if (!n) return "—";
  if (n < 10_000) return "—";   // 나라장터 원천의 1원 등 placeholder 금액은 미표기(utils.ts formatKRW 와 같은 규칙)
  if (n >= 100_000_000) {
    const s = (n / 100_000_000).toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `${s.replace(/\.0$/, "")}억`;
  }
  return `${Math.floor(n / 10_000).toLocaleString("ko-KR")}만`;
}

export function wonFull(v: number | string | null | undefined): string {
  const n = typeof v === "string" ? Number(v) : v;
  if (!n) return "—";
  if (n < 10_000) return "—";   // 나라장터 원천의 1원 등 placeholder 금액은 미표기(utils.ts formatKRW 와 같은 규칙)
  return `${Math.trunc(n).toLocaleString("ko-KR")}원`;
}

/** 한국 시각의 날짜. 서버·브라우저의 로컬 시간대에 의존하지 않는다. */
export function kstDate(date: Date = new Date()): string {
  return date.toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });
}

/** 마감까지 남은 일수. 공고의 날짜와 한국 시각의 오늘을 비교한다. */
export function dLeft(dateStr: string | null | undefined, today: Date = new Date()): { days: number; month: number; day: number } | null {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return null;
  const [y, m, d] = dateStr.slice(0, 10).split("-").map(Number);
  const target = Date.UTC(y, m - 1, d);
  const base = Date.parse(`${kstDate(today)}T00:00:00Z`);
  const days = Math.round((target - base) / 86_400_000);
  return { days, month: m, day: d };
}

export function ymd(s: string | null | undefined): string {
  if (!s) return "—";
  return `${s.slice(0, 4)}.${s.slice(5, 7)}.${s.slice(8, 10)}`;
}

/** 표시용 지역 — 시·도 + 시·군·구까지. 일반구(마산합포구·분당구)·동은 지역 제한 단위가 아니다. */
export function rgnBase(rgn: string | null | undefined): string {
  return (rgn ?? "").split(/\s+/).filter(Boolean).slice(0, 2).join(" ");
}
