import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "jodalfit — 우리 회사에 맞는 공공입찰",
  description:
    "회사명을 입력하면 과거 낙찰 이력과 비교해 따낼 만한 나라장터 공고 TOP 5를 추천해드립니다.",
  metadataBase: new URL("https://jodalfit.co.kr"),
  openGraph: {
    title: "jodalfit",
    description:
      "공공조달, 우리 회사에 맞는 공고만. 과거 낙찰 이력 기반 임베딩 매칭.",
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
        {children}
      </body>
    </html>
  );
}
