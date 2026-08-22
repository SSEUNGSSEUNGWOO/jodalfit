import type { MetadataRoute } from "next";
import { fetchActiveCompaniesForSitemap } from "@/lib/company";
import { fetchRecentNoticesForSitemap } from "@/lib/notice";
import { listAllInsights } from "@/lib/insights";
import {
  COMPANY_SEGMENTS,
  NOTICE_SEGMENT_ID,
  PER_SEGMENT,
  TOTAL_SEGMENTS,
} from "@/lib/sitemap-segments";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

// force-dynamic이라 lastModified에 new Date()를 쓰면 매 요청 값이 바뀐다.
// 크롤러가 lastmod를 신뢰 불가로 판정하면 사이트맵 전체를 무시하므로 고정값을 쓴다.
// 정적 페이지 내용을 실제로 고칠 때만 이 날짜를 갱신할 것.
const STATIC_LASTMOD = new Date("2026-08-17");

// Vercel ISR이 revalidate=86400을 무시하고 며칠~수주간 stale로 서빙하는 이슈로
// Google이 sitemap을 "죽은 사이트"로 판단해 랭킹을 낮춘 사례가 있어 강제 dynamic.
// (히트 빈도 하루 몇 번 수준이라 DB 부담 없음)
export const dynamic = "force-dynamic";

// URL은 /sitemap/{id}.xml 로 나간다. robots.txt가 전 세그먼트를 나열한다.
export async function generateSitemaps() {
  return Array.from({ length: TOTAL_SEGMENTS }, (_, id) => ({ id }));
}

export default async function sitemap({
  id,
}: {
  id: Promise<string>;
}): Promise<MetadataRoute.Sitemap> {
  const segment = Number(await id);

  // 0 ~ COMPANY_SEGMENTS-1: 회사. 색인 대상이 5만 URL 한도를 넘어 나눠 싣는다.
  if (segment < COMPANY_SEGMENTS) {
    try {
      const rows = await fetchActiveCompaniesForSitemap(
        PER_SEGMENT,
        segment * PER_SEGMENT
      );
      return rows
        .filter((r) => /^\d{10}$/.test(r.bizrno_norm))
        .map((r) => ({
          url: `${BASE_URL}/companies/${r.bizrno_norm}`,
          lastModified: r.updated_at ? new Date(r.updated_at) : STATIC_LASTMOD,
          changeFrequency: "weekly" as const,
          priority: 0.6,
        }));
    } catch {
      // 시드 데이터 부족 시 빈 세그먼트. 다른 세그먼트는 그대로 나간다.
      return [];
    }
  }

  // 공고 (라이프사이클 페이지)
  if (segment === NOTICE_SEGMENT_ID) {
    try {
      const rows = await fetchRecentNoticesForSitemap(PER_SEGMENT);
      return rows
        .filter((r) => r.bid_ntce_no)
        .map((r) => ({
          url: `${BASE_URL}/notices/${r.bid_ntce_no}`,
          lastModified: r.updated_at ? new Date(r.updated_at) : STATIC_LASTMOD,
          changeFrequency: "weekly" as const,
          priority: 0.5,
        }));
    } catch {
      return [];
    }
  }

  // 마지막 세그먼트: 정적 라우트 + 인사이트
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "daily",
      priority: 1.0,
    },
    // /recommendations는 noindex(개인화 결과)라 사이트맵에서 제외
    {
      url: `${BASE_URL}/notices`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/companies`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/insights`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/about`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "monthly",
      priority: 0.6,
    },
  ];

  let insightRoutes: MetadataRoute.Sitemap = [];
  try {
    const items = await listAllInsights();
    insightRoutes = items.map((i) => ({
      url: `${BASE_URL}/insights/${i.type}/${i.slug}`,
      lastModified: new Date(i.published_at),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));
  } catch {
    // 인사이트 폴더 없으면 skip
  }

  return [...staticRoutes, ...insightRoutes];
}
