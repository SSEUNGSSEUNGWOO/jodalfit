import type { BidRecommendation, RecommendationResponse } from "@/types/recommendations";

const today = new Date();
const addDays = (n: number) => {
  const d = new Date(today);
  d.setDate(d.getDate() + n);
  return d.toISOString().split("T")[0];
};

export const MOCK_COMPANY = {
  bizrno: "1378802300",
  corp_nm: "주식회사 제이오달소프트",
  rgn_nm: "서울특별시 강남구",
  corp_bsns_div_nm: "소프트웨어개발 / 정보시스템 유지보수",
};

export const MOCK_BIDS: BidRecommendation[] = [
  {
    bid_ntce_no: "R26BK01533268",
    bid_ntce_ord: "000",
    bid_ntce_nm: "한국교육학술정보원 차세대 통합학사관리시스템 유지관리 용역",
    bsns_div_nm: "용역",
    bid_ntce_date: addDays(-2),
    bid_clse_date: addDays(7),
    openg_date: addDays(8),
    presmpt_prce: 178_000_000,
    ntce_instt_nm: "한국교육학술정보원",
    dmnd_instt_nm: "한국교육학술정보원",
    bidprc_psbl_indstryty_nm: "소프트웨어사업자",
    prtcpt_psbl_rgn_nm: "전국",
    bid_ntce_url:
      "https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R26BK01533268&bidPbancOrd=000",
    base_similarity: 0.871,
    bonus: 0.05,
    score: 0.921,
    explanation:
      "최근 3년간 교육기관 대상 시스템 유지보수 수주 이력이 많고, 본 공고의 과업 범위가 기존 낙찰 사업과 매우 유사합니다. 추정가 1.78억과 수행 지역도 기존 수주 패턴에서 크게 벗어나지 않습니다.",
    evidence: ["교육기관 수주 이력 14건", "유지보수 과업 유사", "예산 규모 적합", "마감 여유 7일"],
  },
  {
    bid_ntce_no: "R26BK01533912",
    bid_ntce_ord: "001",
    bid_ntce_nm: "서울특별시교육청 진로진학상담시스템 고도화 용역",
    bsns_div_nm: "용역",
    bid_ntce_date: addDays(-1),
    bid_clse_date: addDays(11),
    openg_date: addDays(12),
    presmpt_prce: 240_000_000,
    ntce_instt_nm: "서울특별시교육청",
    dmnd_instt_nm: "서울특별시교육청",
    bidprc_psbl_indstryty_nm: "소프트웨어사업자, 정보통신공사업",
    prtcpt_psbl_rgn_nm: "서울특별시",
    bid_ntce_url:
      "https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R26BK01533912&bidPbancOrd=001",
    base_similarity: 0.823,
    bonus: 0.05,
    score: 0.873,
    explanation:
      "서울 소재이며 교육청 대상 유사 사업 수주 경험이 충분합니다. 추정가가 평균보다 다소 크지만, 최근 1년 사업 규모가 점진적으로 커지는 추세와 부합합니다.",
    evidence: ["서울 본사 적합", "교육청 과거 수주", "사업 규모 확장 패턴"],
  },
  {
    bid_ntce_no: "R26BK01528732",
    bid_ntce_ord: "000",
    bid_ntce_nm: "국립중앙도서관 디지털콘텐츠관리시스템 개선 용역",
    bsns_div_nm: "용역",
    bid_ntce_date: addDays(-3),
    bid_clse_date: addDays(14),
    openg_date: addDays(15),
    presmpt_prce: 145_000_000,
    ntce_instt_nm: "조달청",
    dmnd_instt_nm: "국립중앙도서관",
    bidprc_psbl_indstryty_nm: "소프트웨어사업자",
    prtcpt_psbl_rgn_nm: "전국",
    bid_ntce_url: "https://www.g2b.go.kr/",
    base_similarity: 0.762,
    bonus: 0.0,
    score: 0.762,
    explanation:
      "정부 공공기관 대상 시스템 개선 사업으로, 회사의 콘텐츠관리 분야 수주 이력과 영역이 겹칩니다. 추정가도 적합 범위 내입니다.",
    evidence: ["공공기관 수주 이력", "콘텐츠관리 영역", "예산 적정"],
  },
  {
    bid_ntce_no: "R26BK01529004",
    bid_ntce_ord: "000",
    bid_ntce_nm: "한국과학기술정보연구원 연구데이터 플랫폼 유지보수 용역",
    bsns_div_nm: "용역",
    bid_ntce_date: addDays(-4),
    bid_clse_date: addDays(2),
    openg_date: addDays(3),
    presmpt_prce: 96_000_000,
    ntce_instt_nm: "한국과학기술정보연구원",
    dmnd_instt_nm: "한국과학기술정보연구원",
    bidprc_psbl_indstryty_nm: "소프트웨어사업자",
    prtcpt_psbl_rgn_nm: "전국",
    bid_ntce_url: "https://www.g2b.go.kr/",
    base_similarity: 0.748,
    bonus: -0.15,
    score: 0.598,
    explanation:
      "연구기관 대상 유지보수 영역이 유사합니다. 다만 마감이 2일 남아 준비 시간이 매우 빠듯합니다. 즉시 검토가 필요한 공고입니다.",
    evidence: ["연구기관 영역", "마감 임박 D-2"],
  },
  {
    bid_ntce_no: "R26BK01529876",
    bid_ntce_ord: "000",
    bid_ntce_nm: "한국방송통신전파진흥원 통합민원시스템 개선 용역",
    bsns_div_nm: "용역",
    bid_ntce_date: addDays(-5),
    bid_clse_date: addDays(18),
    openg_date: addDays(19),
    presmpt_prce: 320_000_000,
    ntce_instt_nm: "한국방송통신전파진흥원",
    dmnd_instt_nm: "한국방송통신전파진흥원",
    bidprc_psbl_indstryty_nm: "소프트웨어사업자, 정보통신공사업",
    prtcpt_psbl_rgn_nm: "전국",
    bid_ntce_url: "https://www.g2b.go.kr/",
    base_similarity: 0.692,
    bonus: 0.0,
    score: 0.692,
    explanation:
      "민원시스템 개선 영역으로 회사가 다룬 적 있는 도메인입니다. 추정가는 평균보다 크지만 수주 패턴이 확장되는 시점에 부합합니다.",
    evidence: ["민원시스템 도메인", "사업 규모 확장"],
  },
];

export const MOCK_RESPONSE: RecommendationResponse = {
  company: MOCK_COMPANY,
  results: MOCK_BIDS,
};
