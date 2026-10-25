// frontend/src/app/sitemap-index.xml/route.ts
// 사이트맵 인덱스 — 세그먼트 9개(/sitemap/0.xml ~ 8.xml, app/sitemap.ts 의 generateSitemaps)를 하나로 가리킨다.
// Next 는 generateSitemaps 를 쓰면 /sitemap.xml 을 만들지 않지만 그 경로를 예약해 두어 라우트 핸들러를 둘 수 없다
// ("Conflicting route and metadata at /sitemap.xml", 2026-10-25) — 그래서 /sitemap-index.xml 이다. robots.txt 에 세그먼트가
// 전부 적혀 있어 구글·네이버는 동작했지만, Bing 웹마스터·다음 검색등록처럼 주소 하나를 받는 곳에 낼 것이 없었다.
import { TOTAL_SEGMENTS } from "@/lib/sitemap-segments";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export const revalidate = 3600;

export function GET() {
  const items = Array.from({ length: TOTAL_SEGMENTS }, (_, i) => `  <sitemap><loc>${BASE_URL}/sitemap/${i}.xml</loc></sitemap>`).join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</sitemapindex>\n`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=3600" } });
}
