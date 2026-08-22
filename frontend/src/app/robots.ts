import type { MetadataRoute } from "next";
import { TOTAL_SEGMENTS } from "@/lib/sitemap-segments";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/"],
      },
      // 네이버 크롤러. "*"로 이미 허용되지만 서치어드바이저 검증에서 명시적으로 보이게 둔다.
      {
        userAgent: "Yeti",
        allow: "/",
        disallow: ["/api/"],
      },
    ],
    // 색인 대상이 5만 URL 한도를 넘어 사이트맵을 세그먼트로 나눴다(lib/sitemap-segments.ts).
    sitemap: Array.from(
      { length: TOTAL_SEGMENTS },
      (_, i) => `${BASE_URL}/sitemap/${i}.xml`
    ),
  };
}
