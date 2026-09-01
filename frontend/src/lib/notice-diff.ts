import { formatDateKR, formatKRW } from "@/lib/utils";

/** 정정 이력 비교용 최소 컬럼 — bid_notices에서 차수별로 읽음 */
export interface NoticeVersion {
  bid_ntce_ord: string;
  bid_ntce_date: string | null;
  bid_ntce_nm: string;
  bid_clse_date: string | null;
  openg_date: string | null;
  presmpt_prce: number | null;
  asign_bdgt_amt: number | null;
  prtcpt_psbl_rgn_nm: string | null;
  bidprc_psbl_indstryty_nm: string | null;
  cntrct_cncls_mthd_nm: string | null;
  bidwinr_dcsn_mthd_nm: string | null;
  attachments: { seq: number; name: string | null; url: string }[] | null;
}

export interface FieldChange {
  label: string;
  before: string;
  after: string;
}

export interface Amendment {
  /** 정정 차수 (1부터) */
  no: number;
  /** 이 차수 공고일 */
  date: string | null;
  /** 비교 대상 이전 차수 (DB에 직전 차수가 없으면 그보다 앞 차수) */
  prevOrd: string;
  changes: FieldChange[];
}

const dash = "—";
const text = (v: string | null | undefined) => (v && v.trim()) || dash;
const date = (v: string | null | undefined) => (v ? formatDateKR(v) : dash);
const money = (v: number | null | undefined) => (v ? formatKRW(v) : dash);

const TRACKED: { key: keyof NoticeVersion; label: string; fmt: (v: never) => string }[] = [
  { key: "bid_ntce_nm", label: "공고명", fmt: text },
  { key: "bid_clse_date", label: "입찰 마감", fmt: date },
  { key: "openg_date", label: "개찰일", fmt: date },
  { key: "presmpt_prce", label: "추정가", fmt: money },
  { key: "asign_bdgt_amt", label: "배정 예산", fmt: money },
  { key: "prtcpt_psbl_rgn_nm", label: "참가가능 지역", fmt: text },
  { key: "bidprc_psbl_indstryty_nm", label: "참가가능 업종", fmt: text },
  { key: "cntrct_cncls_mthd_nm", label: "계약 방법", fmt: text },
  { key: "bidwinr_dcsn_mthd_nm", label: "낙찰 방법", fmt: text },
];

function attachmentNames(v: NoticeVersion): string[] {
  return (v.attachments ?? []).map((a) => a.name ?? `첨부 ${a.seq}`);
}

function diffPair(prev: NoticeVersion, curr: NoticeVersion): FieldChange[] {
  const out: FieldChange[] = [];
  for (const t of TRACKED) {
    const a = prev[t.key] as never;
    const b = curr[t.key] as never;
    if ((a ?? null) === (b ?? null)) continue;
    out.push({ label: t.label, before: t.fmt(a), after: t.fmt(b) });
  }
  const pa = attachmentNames(prev);
  const ca = attachmentNames(curr);
  const added = ca.filter((n) => !pa.includes(n));
  const removed = pa.filter((n) => !ca.includes(n));
  if (added.length || removed.length) {
    out.push({
      label: "첨부파일",
      before: removed.length ? `삭제 ${removed.join(", ")}` : dash,
      after: added.length ? `추가 ${added.join(", ")}` : dash,
    });
  }
  return out;
}

/** 차수 오름차순 버전 목록 → 정정마다 직전 버전과의 변경 목록. 원공고(000)만 있으면 빈 배열 */
export function diffNoticeVersions(versions: NoticeVersion[]): Amendment[] {
  const sorted = [...versions].sort((a, b) => a.bid_ntce_ord.localeCompare(b.bid_ntce_ord));
  const out: Amendment[] = [];
  for (let i = 1; i < sorted.length; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];
    const no = parseInt(curr.bid_ntce_ord, 10);
    if (!Number.isFinite(no) || no <= 0) continue;
    out.push({ no, date: curr.bid_ntce_date, prevOrd: prev.bid_ntce_ord, changes: diffPair(prev, curr) });
  }
  return out.reverse(); // 최신 정정이 위
}
