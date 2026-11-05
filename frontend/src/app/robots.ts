import type { MetadataRoute } from "next";
import { TOTAL_SEGMENTS } from "@/lib/sitemap-segments";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export default function robots(): MetadataRoute.Robots {
  return {
    // /recommendations 는 noindex 인데도 크롤러가 회사 페이지의 "추천 전체 보기" 링크를 따라 들어와 JS 까지 실행해 추천 스트림(LLM 설명 포함)을
    // 하루 1,000번 넘게 돌렸다(2026-10-27~28 meta-externalagent). 색인할 것이 없는 로그인·검토함·결과 경로는 아예 긁지 못하게 한다.
    // /admin 은 적지 않는다 — robots 는 공개 파일이라 경로를 광고하는 꼴이고, 관리자 아니면 404 라 긁어도 색인할 게 없다(check_admin.py 가 검사).
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/recommendations", "/saved", "/welcome", "/consent", "/login", "/signup", "/reset", "/auth/"],
      },
      // 네이버 크롤러. "*"로 이미 허용되지만 서치어드바이저 검증에서 명시적으로 보이게 둔다.
      {
        userAgent: "Yeti",
        allow: "/",
        disallow: ["/api/", "/recommendations", "/saved", "/welcome", "/consent", "/login", "/signup", "/reset", "/auth/"],
      },
      // 검색 노출과 무관한 수집 봇은 통째로 막는다. 회사 페이지 SSR(추천 API self-call) 12시간 3,831건 중
      // AhrefsBot(SEO 데이터 판매) 825 + KeenableBot(AI 검색 API 업체 색인) 554 = 36%(2026-11-05, search_logs.user_agent).
      // Keenable 은 공식 이름이 Keenable-SearchBot 인데 로그엔 KeenableBot 으로 찍혀 둘 다 적는다.
      { userAgent: ["AhrefsBot", "KeenableBot", "Keenable-SearchBot"], disallow: "/" },
    ],
    // 색인 대상이 5만 URL 한도를 넘어 사이트맵을 세그먼트로 나눴다(lib/sitemap-segments.ts).
    sitemap: Array.from(
      { length: TOTAL_SEGMENTS },
      (_, i) => `${BASE_URL}/sitemap/${i}.xml`
    ),
  };
}
