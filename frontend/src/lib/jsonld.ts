// JSON-LD 구조화 데이터 헬퍼.
// 페이지 컴포넌트에서 <JsonLd data={...} /> 또는 직접 <script> 삽입.

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export type Json = Record<string, unknown>;

/** <script type="application/ld+json"> 의 안전한 직렬화 (XSS 방어). */
export function serializeJsonLd(data: Json | Json[]): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

/** 사이트 운영 조직 — 루트 레이아웃에 1회. */
export function organizationJsonLd(): Json {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    // 한글이 주 이름이다 — 구글 검색결과의 사이트명은 WebSite/Organization 의 name 을 쓰고, 영문이면
    // 도메인(jodalfit.co.kr)으로 대체됐다(2026-10-26 확인). AI 답변·검색도 한글 이름으로 묻는다(GEO, 2026-10-24).
    name: "조달핏",
    alternateName: "jodalfit",
    url: SITE_URL,
    logo: `${SITE_URL}/icon.svg`,
    description:
      "회사명만 입력하면 등록업종·공급물품·수주 이력 기반으로 검토할 만한 나라장터 공고를 추천합니다.",
    // sameAs는 실제 공식 프로필(블로그·SNS)이 생기면 채운다 — 빈 배열은 검증 도구가 지적함
  };
}

/** 사이트 이름(검색결과 첫 줄 "조달핏") + 검색박스 — 구글은 홈의 WebSite.name 을 사이트명으로 쓴다. */
export function websiteJsonLd(): Json {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    url: SITE_URL,
    name: "조달핏",
    alternateName: "jodalfit",
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

/** 자주 묻는 질문 — /faq. 화면의 질문·답과 같은 문장이어야 한다(구글 FAQ 지침: 보이는 내용만). */
export function faqJsonLd(items: readonly { q: string; a: string }[]): Json {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((it) => ({
      "@type": "Question",
      name: it.q,
      acceptedAnswer: { "@type": "Answer", text: it.a },
    })),
  };
}

/** 회사 페이지에 노출할 분석 대상 회사. */
// 대표자명은 개인사업자의 경우 개인정보에 해당해 구조화 데이터에 넣지 않는다.
export function companyOrganizationJsonLd(args: {
  bizrnoNorm: string;
  corpNm: string;
  rgnNm?: string | null;
  industriesSummary?: string | null;
}): Json {
  const { bizrnoNorm, corpNm, rgnNm, industriesSummary } = args;
  const data: Json = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: corpNm,
    identifier: bizrnoNorm,
    url: `${SITE_URL}/companies/${bizrnoNorm}`,
  };
  if (industriesSummary) data.description = industriesSummary;
  if (rgnNm) data.address = { "@type": "PostalAddress", addressRegion: rgnNm, addressCountry: "KR" };
  return data;
}

/** 회사 페이지 브레드크럼 — 검색결과 둘째 줄이 "jodalfit.co.kr › companies" 대신 "조달핏 › 공공조달 활동 기업 › 대구광역시 › 회사명"
 *  으로 나오게(경쟁 페이지는 지역까지 보여 준다, 2026-10-26). sido 는 /companies/browse/[sido]/1 이 있는 시·도만 넣는다 —
 *  구글은 마지막 항목 외엔 item(URL)이 필수다. */
export function companyBreadcrumbJsonLd(args: { bizrnoNorm: string; corpNm: string; sido?: string | null }): Json {
  const { bizrnoNorm, corpNm, sido } = args;
  const items: Json[] = [
    { "@type": "ListItem", name: "홈", item: SITE_URL },
    { "@type": "ListItem", name: "공공조달 활동 기업", item: `${SITE_URL}/companies` },
  ];
  if (sido) items.push({ "@type": "ListItem", name: sido, item: `${SITE_URL}/companies/browse/${encodeURIComponent(sido)}/1` });
  items.push({ "@type": "ListItem", name: corpNm, item: `${SITE_URL}/companies/${bizrnoNorm}` });
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({ ...it, position: i + 1 })),
  };
}

/** 입찰공고 상세 — WebPage + BreadcrumbList.
 *  (GovernmentService는 "기관이 제공하는 행정 서비스" 의미라 입찰공고에 맞지 않음) */
export function noticeJsonLd(args: {
  bidNtceNo: string;
  bidNtceNm: string;
  description: string;
  instituionName?: string | null;
  regionName?: string | null;
  validFrom?: string | null;
  validThrough?: string | null;
}): Json[] {
  const { bidNtceNo, bidNtceNm, description, instituionName, validFrom, validThrough } = args;
  const url = `${SITE_URL}/notices/${bidNtceNo}`;
  const page: Json = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: bidNtceNm,
    description,
    url,
    isPartOf: { "@type": "WebSite", url: SITE_URL, name: "조달핏" },
  };
  if (instituionName) {
    page.about = { "@type": "GovernmentOrganization", name: instituionName };
  }
  if (validFrom) page.datePublished = validFrom;
  if (validThrough) page.dateModified = validThrough;
  const breadcrumb: Json = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "공고 둘러보기", item: `${SITE_URL}/notices` },
      { "@type": "ListItem", position: 3, name: bidNtceNm, item: url },
    ],
  };
  return [page, breadcrumb];
}
