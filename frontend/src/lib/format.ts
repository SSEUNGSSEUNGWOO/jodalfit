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

/** 마감까지 남은 일수. 날짜 문자열 앞 10자리만 쓴다(시간대 무시 — 나라장터 마감은 날짜 단위로 본다). */
export function dLeft(dateStr: string | null | undefined, today: Date = new Date()): { days: number; month: number; day: number } | null {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return null;
  const [y, m, d] = dateStr.slice(0, 10).split("-").map(Number);
  const target = new Date(y, m - 1, d);
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((target.getTime() - base.getTime()) / 86_400_000);
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
