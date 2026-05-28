import "server-only";
import { cache } from "react";
import { fetchCompanyProfile, fetchCompanyContracts } from "./company";

/** 회사 활동 영역 분석 — 등록업종·공급물품·수주 이력 텍스트에서 키워드 매칭으로 영역 분포 계산.
 *  목적: 다부서 회사(예: 케이브레인컴퍼니) 검출 → 키워드 모드 안내.
 *  방식: 미리 정의한 영역 사전(`DOMAIN_KEYWORDS`)에 substring 매칭. LLM/임베딩 없이 빠른 분류.
 */
export type CompanyDomain =
  | "it"
  | "content"
  | "education"
  | "hrd"
  | "consulting"
  | "ai"
  | "design"
  | "event"
  | "construction"
  | "medical";

export const DOMAIN_LABELS: Record<CompanyDomain, string> = {
  it: "IT·시스템",
  content: "콘텐츠 개발",
  education: "교육·학술",
  hrd: "HRD·연수",
  consulting: "컨설팅",
  ai: "AI·데이터",
  design: "디자인",
  event: "행사·대행",
  construction: "건설",
  medical: "의료·보건",
};

/** 키워드 모드(/recommendations?q=) 검색용 대표 키워드 — 칩 클릭 시 라우팅. */
export const DOMAIN_SUGGESTED_KEYWORD: Record<CompanyDomain, string> = {
  it: "시스템 구축",
  content: "콘텐츠 개발",
  education: "교육 운영",
  hrd: "위탁교육 연수",
  consulting: "컨설팅",
  ai: "AI 데이터",
  design: "디자인",
  event: "행사 대행",
  construction: "건설 공사",
  medical: "의료 보건",
};

/** 키워드 사전. 케이스 무시(소문자 정규화), substring 매칭. 한 키워드가 여러 도메인에 속할 수 있음. */
const DOMAIN_KEYWORDS: Record<CompanyDomain, string[]> = {
  it: [
    "소프트웨어",
    "sw",
    "시스템",
    "정보시스템",
    "패키지",
    "데이터베이스",
    "컴퓨터",
    "네트워크",
    "서버",
    "클라우드",
    "erp",
    "인프라",
    "웹",
    "앱",
    "어플",
    "유지관리",
    "유지보수",
    "구축",
    "포털",
    "솔루션",
    "전산",
    "정보화",
  ],
  content: [
    "디지털콘텐츠",
    "콘텐츠",
    "영상",
    "비디오",
    "미디어",
    "게임",
    "방송",
    "애니메이션",
    "이러닝",
    "vr",
    "ar",
    "xr",
    "실감",
    "미디어아트",
  ],
  education: [
    "교육",
    "학술",
    "연구",
    "학습",
    "평생교육",
    "강의",
    "학교",
    "대학",
    "원격",
    "교과",
    "학생",
    "교원",
    "교수",
    "수업",
    "온라인교육",
  ],
  hrd: [
    "위탁교육",
    "위탁운영",
    "직무",
    "리더십",
    "신입",
    "승진",
    "승격",
    "인재",
    "인재개발",
    "연수",
    "워크숍",
    "역량강화",
    "공통역량",
    "양성",
    "직급",
    "실무",
  ],
  consulting: [
    "컨설팅",
    "진단",
    "자문",
    "감리",
    "전략",
    "isp",
    "마스터플랜",
    "조직진단",
    "타당성",
    "정책",
    "평가",
  ],
  ai: [
    "ai",
    "인공지능",
    "ml",
    "머신러닝",
    "딥러닝",
    "데이터",
    "dx",
    "ax",
    "빅데이터",
    "챗봇",
    "분석모델",
    "생성형",
  ],
  design: [
    "디자인",
    "ui",
    "ux",
    "그래픽",
    "시각",
    "환경디자인",
    "산업디자인",
  ],
  event: [
    "행사",
    "이벤트",
    "대행",
    "운영대행",
    "박람회",
    "페스티벌",
    "축제",
    "회의기획",
    "기념",
    "전시",
  ],
  construction: [
    "공사",
    "건축",
    "토목",
    "신축",
    "증축",
    "도로",
    "정비공사",
    "리모델링",
    "포장",
    "교량",
  ],
  medical: [
    "의료",
    "보건",
    "의약품",
    "진료",
    "병원",
    "약품",
    "보건소",
    "의료기기",
  ],
};

export interface DomainStat {
  domain: CompanyDomain;
  label: string;
  count: number;
  /** 전체 매칭 합 대비 비율 (0~1) */
  ratio: number;
  suggestedKeyword: string;
}

export interface CompanyDomainAnalysis {
  /** 매칭된 영역들 (비율 내림차순). */
  domains: DomainStat[];
  /** 1위 영역의 비율. */
  dominantRatio: number;
  /** 다부서 회사 판정 — 1위 < 50% 또는 영역 수 >= 4. */
  isMultiDept: boolean;
  /** 분석 입력의 텍스트 토큰 수 (디버깅용). */
  totalHits: number;
}

interface AnalysisInput {
  industries: string[];
  products: string[];
  contractNames: string[];
}

export function analyzeCompanyDomains(
  input: AnalysisInput
): CompanyDomainAnalysis {
  const text = [
    ...input.industries,
    ...input.products,
    ...input.contractNames,
  ]
    .join(" ")
    .toLowerCase();

  const counts = new Map<CompanyDomain, number>();
  for (const [domain, keywords] of Object.entries(DOMAIN_KEYWORDS) as [
    CompanyDomain,
    string[],
  ][]) {
    let count = 0;
    for (const kw of keywords) {
      // 단순 substring 매칭 (한글에 단어 경계 적용 어려움)
      const lowered = kw.toLowerCase();
      let idx = 0;
      while ((idx = text.indexOf(lowered, idx)) !== -1) {
        count++;
        idx += lowered.length;
      }
    }
    if (count > 0) counts.set(domain, count);
  }

  const totalHits = Array.from(counts.values()).reduce((s, v) => s + v, 0);
  if (totalHits === 0) {
    return { domains: [], dominantRatio: 0, isMultiDept: false, totalHits: 0 };
  }

  const domains: DomainStat[] = Array.from(counts.entries())
    .map(([domain, count]) => ({
      domain,
      label: DOMAIN_LABELS[domain],
      count,
      ratio: count / totalHits,
      suggestedKeyword: DOMAIN_SUGGESTED_KEYWORD[domain],
    }))
    .sort((a, b) => b.count - a.count);

  const dominantRatio = domains[0].ratio;
  const isMultiDept = dominantRatio < 0.5 || domains.length >= 4;

  return { domains, dominantRatio, isMultiDept, totalHits };
}

/** 회사 페이지에서 호출. React cache로 동일 페이지 내 dedupe. */
export const fetchCompanyDomainAnalysis = cache(
  async (bizrnoNorm: string): Promise<CompanyDomainAnalysis> => {
    const [profile, contracts] = await Promise.all([
      fetchCompanyProfile(bizrnoNorm),
      fetchCompanyContracts(bizrnoNorm, 50),
    ]);
    return analyzeCompanyDomains({
      industries: profile.industries,
      products: profile.products,
      contractNames: contracts
        .map((c) => c.cntrct_nm)
        .filter((n): n is string => !!n),
    });
  }
);
