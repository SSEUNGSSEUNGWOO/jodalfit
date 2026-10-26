import type { Metadata } from "next";
import { organizationJsonLd, serializeJsonLd, websiteJsonLd } from "@/lib/jsonld";
import "./globals.css";

export const metadata: Metadata = {
  // 페이지가 메타를 안 주는 응답(404 등)의 폴백 — 공문 톤, 점수·건수 약속 없음
  title: "조달핏 — 우리 회사에 맞는 공공입찰",
  description:
    "회사명 또는 사업자등록번호를 입력하면 등록업종·공급물품·수주 이력으로 지금 입찰 가능한 나라장터 공고 중 검토할 만한 것을 추립니다.",
  metadataBase: new URL("https://jodalfit.co.kr"),
  openGraph: {
    siteName: "조달핏", // 검색결과 사이트명의 보조 신호(주 신호는 WebSite JSON-LD의 name)
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
