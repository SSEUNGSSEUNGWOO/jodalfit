import type { MetadataRoute } from "next";
import { TOTAL_SEGMENTS } from "@/lib/sitemap-segments";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export default function robots(): MetadataRoute.Robots {
  return {
    // /recommendations 는 noindex 인데도 크롤러가 회사 페이지의 "추천 전체 보기" 링크를 따라 들어와 JS 까지 실행해 추천 스트림(LLM 설명 포함)을
    // 하루 1,000번 넘게 돌렸다(2026-10-27~28 meta-externalagent). 색인할 것이 없는 로그인·검토함·결과 경로는 아예 긁지 못하게 한다.
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/recommendations", "/saved", "/welcome", "/consent", "/login", "/signup", "/reset", "/auth/", "/admin"],
      },
      // 네이버 크롤러. "*"로 이미 허용되지만 서치어드바이저 검증에서 명시적으로 보이게 둔다.
      {
        userAgent: "Yeti",
        allow: "/",
        disallow: ["/api/", "/recommendations", "/saved", "/welcome", "/consent", "/login", "/signup", "/reset", "/auth/", "/admin"],
      },
    ],
    // 색인 대상이 5만 URL 한도를 넘어 사이트맵을 세그먼트로 나눴다(lib/sitemap-segments.ts).
    sitemap: Array.from(
      { length: TOTAL_SEGMENTS },
      (_, i) => `${BASE_URL}/sitemap/${i}.xml`
    ),
  };
}
