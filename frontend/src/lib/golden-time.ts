import type { NoticeLifecycle, PreSpec, BidNotice } from "./notice";

/** 공공조달 골든타임 — 사전규격공개 단계에서 사양에 의견을 낼 수 있는 마지막 시점.
 *
 *  법정 기간 (조달청 안내):
 *  - 일반사업: 사전규격공개 5일 이상
 *  - SW사업 총사업 5억원 이상: 10일 이상
 *  - 긴급: 3일 이상
 *
 *  본공고가 게시되면 사양 변경이 어렵기 때문에 사전규격 단계가 영업·기술협의의 핵심 타이밍.
 */
export type GoldenTimeStatus =
  /** 발주계획만 있고 사전규격 아직 안 뜸 */
  | "planning"
  /** 사전규격 공개중, 의견 마감 D-3 이상 */
  | "spec_open"
  /** 사전규격 공개중, 의견 마감 D-0~D-2 (임박) */
  | "spec_closing"
  /** 본공고가 게시됨 (사전규격은 있었거나 없었거나) — 골든타임 지남 */
  | "notice_active"
  /** 입찰 마감/낙찰/계약 — 종료 */
  | "closed";

export interface GoldenTimeInfo {
  status: GoldenTimeStatus;
  /** 의견 등록 마감일까지 남은 일수 (사전규격 단계일 때만 유의미). 마감일 미상이면 null. */
  opinionDaysLeft: number | null;
  /** 의견 등록 마감 날짜 (YYYY-MM-DD). 없으면 null. */
  opinionDeadline: string | null;
  /** 사양서 PDF URL이 공개되어 있나 */
  hasSpecPdf: boolean;
  /** 사전규격에 등록된 의견 수 */
  opinionCount: number;
  /** SW사업 여부 (Y면 10일 이상 사전규격공개) */
  isSwBiz: boolean;
}

/** YYYY-MM-DD 형식 날짜 문자열을 받아 오늘 기준 남은 일수를 반환. 잘못된 형식이면 null. */
function daysFromToday(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  // "2026-06-01" 또는 "2026-06-01 12:34:56" 양쪽 지원
  const datePart = dateStr.split(" ")[0];
  const d = new Date(`${datePart}T00:00:00`);
  if (isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffMs = d.getTime() - today.getTime();
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

/** 사전규격 중 가장 의견 마감이 늦은 것 (= 아직 열려 있을 가능성 큰 것)을 골라 분석. */
function pickActiveSpec(preSpecs: PreSpec[]): PreSpec | null {
  if (preSpecs.length === 0) return null;
  // opnin_rgst_clse_dt가 있는 것 중 가장 늦은 것
  const withDeadline = preSpecs.filter((s) => s.opnin_rgst_clse_dt);
  if (withDeadline.length === 0) return preSpecs[0]; // 마감일 모르면 첫 번째라도
  return withDeadline.reduce((latest, cur) => {
    const a = new Date((latest.opnin_rgst_clse_dt ?? "").split(" ")[0]).getTime();
    const b = new Date((cur.opnin_rgst_clse_dt ?? "").split(" ")[0]).getTime();
    return b > a ? cur : latest;
  });
}

function isNoticeActive(notice: BidNotice): boolean {
  if (!notice.bid_ntce_date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const clse = notice.bid_clse_date ? new Date(`${notice.bid_clse_date}T00:00:00`) : null;
  return !clse || today <= clse;
}

function isNoticeClosed(data: NoticeLifecycle): boolean {
  if (data.contracts.length > 0 || data.awards.length > 0) return true;
  if (data.notice.bid_clse_date) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const clse = new Date(`${data.notice.bid_clse_date}T00:00:00`);
    if (today > clse) return true;
  }
  return false;
}

export function analyzeGoldenTime(data: NoticeLifecycle): GoldenTimeInfo {
  const activeSpec = pickActiveSpec(data.preSpecs);
  const opinionDeadlineRaw = activeSpec?.opnin_rgst_clse_dt ?? null;
  const opinionDeadline = opinionDeadlineRaw?.split(" ")[0] ?? null;
  const opinionDaysLeft = daysFromToday(opinionDeadlineRaw);
  const hasSpecPdf = !!activeSpec?.spec_doc_file_url_1;
  const opinionCount = data.opinions.length;
  const isSwBiz = activeSpec?.sw_biz_obj_yn === "Y";

  const base = {
    opinionDaysLeft,
    opinionDeadline,
    hasSpecPdf,
    opinionCount,
    isSwBiz,
  };

  if (isNoticeClosed(data)) return { ...base, status: "closed" };
  if (isNoticeActive(data.notice)) return { ...base, status: "notice_active" };

  if (data.preSpecs.length > 0) {
    // 사전규격은 있는데 본공고는 아직 — 골든타임 가능
    if (opinionDaysLeft !== null) {
      if (opinionDaysLeft < 0) {
        // 의견 마감 지남, 본공고 대기 — 골든타임 종료지만 본공고는 아직
        return { ...base, status: "notice_active" };
      }
      if (opinionDaysLeft <= 2) return { ...base, status: "spec_closing" };
      return { ...base, status: "spec_open" };
    }
    // 마감일 모르지만 사전규격은 등록되어 있음 — 일단 열려 있다고 가정
    return { ...base, status: "spec_open" };
  }

  if (data.orderPlans.length > 0) return { ...base, status: "planning" };

  // 어떤 단계 정보도 없음 — 본공고가 활성이 아니면 closed로 처리
  return { ...base, status: "closed" };
}

export function isGoldenTime(status: GoldenTimeStatus): boolean {
  return status === "spec_open" || status === "spec_closing";
}

/** UI 표시용 라벨 */
export const GOLDEN_TIME_LABEL: Record<GoldenTimeStatus, string> = {
  planning: "발주 계획 단계",
  spec_open: "골든타임 · 사전규격 공개중",
  spec_closing: "골든타임 마감 임박",
  notice_active: "입찰공고 진행중",
  closed: "종료",
};
