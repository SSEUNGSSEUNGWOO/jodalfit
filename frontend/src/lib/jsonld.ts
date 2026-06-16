// JSON-LD 구조화 데이터 헬퍼.
// 페이지 컴포넌트에서 <JsonLd data={...} /> 또는 직접 <script> 삽입.

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

type Json = Record<string, unknown>;

/** <script type="application/ld+json"> 의 안전한 직렬화 (XSS 방어). */
export function serializeJsonLd(data: Json | Json[]): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

/** 사이트 운영 조직 — 루트 레이아웃에 1회. */
export function organizationJsonLd(): Json {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "jodalfit",
    url: SITE_URL,
    logo: `${SITE_URL}/icon.svg`,
    description:
      "회사명만 입력하면 등록업종·공급물품·수주 이력 기반으로 검토할 만한 나라장터 공고를 추천합니다.",
    sameAs: [],
  };
}

/** 사이트 검색박스 — 구글이 사이트링크 검색박스 노출에 사용. */
export function websiteJsonLd(): Json {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    url: SITE_URL,
    name: "jodalfit",
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${SITE_URL}/recommendations?company={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  };
}

/** 회사 페이지에 노출할 분석 대상 회사. */
export function companyOrganizationJsonLd(args: {
  bizrnoNorm: string;
  corpNm: string;
  ceoNm?: string | null;
  rgnNm?: string | null;
  industriesSummary?: string | null;
}): Json {
  const { bizrnoNorm, corpNm, ceoNm, rgnNm, industriesSummary } = args;
  const data: Json = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: corpNm,
    identifier: bizrnoNorm,
    url: `${SITE_URL}/companies/${bizrnoNorm}`,
  };
  if (industriesSummary) data.description = industriesSummary;
  if (rgnNm) data.address = { "@type": "PostalAddress", addressRegion: rgnNm, addressCountry: "KR" };
  if (ceoNm) {
    data.employee = { "@type": "Person", name: ceoNm, jobTitle: "대표" };
  }
  return data;
}

/** 입찰공고 — GovernmentService(발주기관이 제공하는 조달 서비스)로 표현. */
export function noticeJsonLd(args: {
  bidNtceNo: string;
  bidNtceNm: string;
  description: string;
  instituionName?: string | null;
  regionName?: string | null;
  validFrom?: string | null;
  validThrough?: string | null;
}): Json {
  const { bidNtceNo, bidNtceNm, description, instituionName, regionName, validFrom, validThrough } = args;
  const data: Json = {
    "@context": "https://schema.org",
    "@type": "GovernmentService",
    name: bidNtceNm,
    identifier: bidNtceNo,
    description,
    url: `${SITE_URL}/notices/${bidNtceNo}`,
  };
  if (instituionName) {
    data.provider = {
      "@type": "GovernmentOrganization",
      name: instituionName,
    };
  }
  if (regionName) {
    data.areaServed = { "@type": "AdministrativeArea", name: regionName };
  }
  if (validFrom) data.validFrom = validFrom;
  if (validThrough) data.validThrough = validThrough;
  return data;
}
