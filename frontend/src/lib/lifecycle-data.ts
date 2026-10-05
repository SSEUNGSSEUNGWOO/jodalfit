import type { Award, Contract, NoticeLifecycle, OrderPlan, PreSpec } from "./notice";

/** 공고 상세의 클라이언트 컴포넌트(Lifecycle·GoldenTimeBanner)에 넘기는 최소 데이터.
 *  NoticeLifecycle 전체를 넘기면 첨부 인사이트·의견 본문·정정 이력까지 RSC payload로 직렬화돼
 *  ISR Write 단위(8KB)가 그만큼 늘어난다. 두 컴포넌트가 실제로 읽는 필드만 담는다. */
export interface LifecycleData {
  notice: { bid_ntce_date: string | null; bid_clse_date: string | null };
  preSpecs: Pick<PreSpec, "rgst_dt" | "opnin_rgst_clse_dt" | "spec_doc_file_url_1" | "sw_biz_obj_yn">[];
  opinionCount: number;
  orderPlans: Pick<OrderPlan, "order_year" | "order_mnth">[];
  awards: Pick<Award, "corp_nm" | "bid_amt">[];
  contracts: Pick<Contract, "cntrct_cncls_date">[];
}

export function toLifecycleData(d: NoticeLifecycle): LifecycleData {
  return {
    notice: { bid_ntce_date: d.notice.bid_ntce_date, bid_clse_date: d.notice.bid_clse_date },
    preSpecs: d.preSpecs.map((s) => ({
      rgst_dt: s.rgst_dt,
      opnin_rgst_clse_dt: s.opnin_rgst_clse_dt,
      spec_doc_file_url_1: s.spec_doc_file_url_1,
      sw_biz_obj_yn: s.sw_biz_obj_yn,
    })),
    opinionCount: d.opinions.length,
    orderPlans: d.orderPlans.map((p) => ({ order_year: p.order_year, order_mnth: p.order_mnth })),
    awards: d.awards.map((a) => ({ corp_nm: a.corp_nm, bid_amt: a.bid_amt })),
    contracts: d.contracts.map((c) => ({ cntrct_cncls_date: c.cntrct_cncls_date })),
  };
}
