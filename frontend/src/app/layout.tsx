import type { Metadata } from "next";
import { organizationJsonLd, serializeJsonLd, websiteJsonLd } from "@/lib/jsonld";
import "./globals.css";

export const metadata: Metadata = {
  title: "조달핏 — 우리 회사에 맞는 공공입찰",
  description:
    "회사명만 입력하면 등록업종·공급물품·수주 이력을 함께 분석해 지금 검토할 만한 나라장터 공고 TOP 5를 알려드려요.",
  metadataBase: new URL("https://jodalfit.co.kr"),
  openGraph: {
    title: "조달핏",
    description:
      "공공조달, 우리 회사가 검토할 만한 공고만. 등록업종·공급물품 기반 매칭.",
    type: "website",
    locale: "ko_KR",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full flex flex-col bg-background text-foreground antialiased">
        <span
          hidden
          dangerouslySetInnerHTML={{
            __html: `<!--
THESIS: 추천 결과는 카드 피드가 아니라 공식 개찰판이다 - 봉인된 공고가 번호 행으로 도열하고, 행이 "개봉"되며 근거를 내보인다. SaaS 카드 대시보드 배치를 거부한다.
OWN-WORLD (청색 장부 렌디션, 2026-08-16 사용자 확정): 차가운 장부지(#F6F8FB) 위 괘선 보드, 네이비(#1E3A66) 밴드가 판머리·구독대를 소유, 청람 잉크(#17233A) 활자, 옅은 청색 틴트(#E5EDF8) 칩 - 인주(#B23A2A)는 마감 임박과 저장 인장에만 남는 유일한 붉은 사건. 명조(Noto Serif KR) 판머리 + 본문 워크호스 산세리프, 전 수치 tabular.
STORY: 매일 아침 들르는 담당자가 오늘의 개찰판을 훑고, 행을 개봉해 근거를 확인하고, 검토할 공고에 도장을 찍어 목록에 남긴 뒤 다시 온다.
FIRST VIEWPORT: 크라프트 판머리(회사명 명조 대활자 + 기준·갱신 메타 + 관인) 아래 조회 조건 캡슐 바, 이어 괘선 개찰판 1~5행 - 순번/공고/마감/추정가/적합이 공유 괘선에 정렬, 1행은 개봉된 상태로 근거를 내보인다. 주 액션은 행 개봉과 도장(저장).
FORM: 개찰판(開札板) - 자체 후보 7순위, seed key f3792acf.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
-->`,
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: serializeJsonLd([organizationJsonLd(), websiteJsonLd()]),
          }}
        />
        {children}
      </body>
    </html>
  );
}
