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
