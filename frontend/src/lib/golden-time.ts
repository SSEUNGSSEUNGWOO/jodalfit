import "server-only";
import type { NoticeLifecycle, PreSpec, BidNotice } from "./notice";
import { getServerSupabase } from "./supabase-server";

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

/** lifecycle에서 분리된 부분 정보로 골든타임 분석 (batch 케이스용). */
export function analyzeGoldenTimeFromParts(args: {
  notice: Pick<BidNotice, "bid_ntce_date" | "bid_clse_date">;
  preSpecs: PreSpec[];
  opinionCount: number;
  hasAwardsOrContracts: boolean;
  hasOrderPlans: boolean;
}): GoldenTimeInfo {
  const { notice, preSpecs, opinionCount, hasAwardsOrContracts, hasOrderPlans } = args;
  const activeSpec = pickActiveSpec(preSpecs);
  const opinionDeadlineRaw = activeSpec?.opnin_rgst_clse_dt ?? null;
  const opinionDeadline = opinionDeadlineRaw?.split(" ")[0] ?? null;
  const opinionDaysLeft = daysFromToday(opinionDeadlineRaw);
  const hasSpecPdf = !!activeSpec?.spec_doc_file_url_1;
  const isSwBiz = activeSpec?.sw_biz_obj_yn === "Y";

  const base = {
    opinionDaysLeft,
    opinionDeadline,
    hasSpecPdf,
    opinionCount,
    isSwBiz,
  };

  // closed: 낙찰/계약 있거나 마감일 지남
  if (hasAwardsOrContracts) return { ...base, status: "closed" };
  if (notice.bid_clse_date) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const clse = new Date(`${notice.bid_clse_date}T00:00:00`);
    if (today > clse) return { ...base, status: "closed" };
  }

  // notice_active: 본공고가 떴고 마감 안 지남
  if (notice.bid_ntce_date) {
    return { ...base, status: "notice_active" };
  }

  if (preSpecs.length > 0) {
    if (opinionDaysLeft !== null) {
      if (opinionDaysLeft < 0) return { ...base, status: "notice_active" };
      if (opinionDaysLeft <= 2) return { ...base, status: "spec_closing" };
      return { ...base, status: "spec_open" };
    }
    return { ...base, status: "spec_open" };
  }

  if (hasOrderPlans) return { ...base, status: "planning" };

  return { ...base, status: "closed" };
}

export function analyzeGoldenTime(data: NoticeLifecycle): GoldenTimeInfo {
  return analyzeGoldenTimeFromParts({
    notice: data.notice,
    preSpecs: data.preSpecs,
    opinionCount: data.opinions.length,
    hasAwardsOrContracts: data.awards.length > 0 || data.contracts.length > 0,
    hasOrderPlans: data.orderPlans.length > 0,
  });
}

/** 추천 결과 등 여러 공고를 한 번에 분석. 사전규격·의견 정보만 batch 조회.
 *  본공고 상태(bid_ntce_date, bid_clse_date)는 호출자가 BidRecommendation에서 전달.
 *  낙찰/계약 정보까지 매번 조회하면 비싸므로 false로 가정 (추천 대상은 active 공고). */
export async function fetchGoldenTimeMap(
  notices: { bid_ntce_no: string; bid_ntce_date: string | null; bid_clse_date: string | null }[]
): Promise<Map<string, GoldenTimeInfo>> {
  const result = new Map<string, GoldenTimeInfo>();
  if (notices.length === 0) return result;

  const c = getServerSupabase();
  const bidNtceNos = notices.map((n) => n.bid_ntce_no);

  // pre_specs는 bid_ntce_no_list가 콤마구분 문자열일 가능성 — 1차 MVP는 ilike로 OR 조회
  // Supabase에서 IN으로 ilike 패턴 매칭은 못 하니 .or()로 조립
  const orClause = bidNtceNos
    .map((no) => `bid_ntce_no_list.ilike.%${no}%`)
    .join(",");

  const { data: specRows } = await c
    .from("pre_specs")
    .select(
      "bf_spec_rgst_no,bid_ntce_no_list,prdct_clsfc_no_nm,bsns_div_nm,sw_biz_obj_yn,asign_bdgt_amt,rcpt_dt,rgst_dt,opnin_rgst_clse_dt,order_instt_nm,rl_dminstt_nm,spec_doc_file_url_1"
    )
    .or(orClause)
    .limit(500);

  type SpecRow = PreSpec & { bid_ntce_no_list: string | null };
  const specsByNotice = new Map<string, PreSpec[]>();
  const specIdToNotice = new Map<string, string[]>(); // bf_spec_rgst_no → 해당 공고들
  for (const row of (specRows as SpecRow[]) ?? []) {
    if (!row.bid_ntce_no_list) continue;
    const matchingNos = bidNtceNos.filter((no) =>
      row.bid_ntce_no_list!.includes(no)
    );
    if (matchingNos.length === 0) continue;
    const { bid_ntce_no_list, ...spec } = row;
    void bid_ntce_no_list;
    for (const no of matchingNos) {
      const arr = specsByNotice.get(no) ?? [];
      arr.push(spec as PreSpec);
      specsByNotice.set(no, arr);
      const noticesForSpec = specIdToNotice.get(spec.bf_spec_rgst_no) ?? [];
      noticesForSpec.push(no);
      specIdToNotice.set(spec.bf_spec_rgst_no, noticesForSpec);
    }
  }

  // 의견 수만 필요 — 전체 의견 fetch는 비싸니 count만
  const opinionCountByNotice = new Map<string, number>();
  if (specIdToNotice.size > 0) {
    const allSpecIds = Array.from(specIdToNotice.keys());
    const { data: opRows } = await c
      .from("pre_spec_opinions")
      .select("bf_spec_rgst_no")
      .in("bf_spec_rgst_no", allSpecIds);
    for (const row of (opRows as { bf_spec_rgst_no: string }[]) ?? []) {
      const noticesForSpec = specIdToNotice.get(row.bf_spec_rgst_no) ?? [];
      for (const no of noticesForSpec) {
        opinionCountByNotice.set(no, (opinionCountByNotice.get(no) ?? 0) + 1);
      }
    }
  }

  for (const n of notices) {
    const preSpecs = specsByNotice.get(n.bid_ntce_no) ?? [];
    const info = analyzeGoldenTimeFromParts({
      notice: { bid_ntce_date: n.bid_ntce_date, bid_clse_date: n.bid_clse_date },
      preSpecs,
      opinionCount: opinionCountByNotice.get(n.bid_ntce_no) ?? 0,
      hasAwardsOrContracts: false, // 추천 대상은 active라고 가정 (closed는 추천에 안 들어옴)
      hasOrderPlans: false,
    });
    result.set(n.bid_ntce_no, info);
  }

  return result;
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
