import type { MetadataRoute } from "next";
import { fetchActiveCompaniesForSitemap } from "@/lib/company";
import { fetchRecentNoticesForSitemap } from "@/lib/notice";
import { listAllInsights } from "@/lib/insights";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

// Vercel ISR이 revalidate=86400을 무시하고 며칠~수주간 stale로 서빙하는 이슈로
// Google이 sitemap을 "죽은 사이트"로 판단해 랭킹을 낮춘 사례가 있어 강제 dynamic.
// (히트 빈도 하루 몇 번 수준이라 DB 부담 없음)
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  // Static routes
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/recommendations`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/insights`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/about`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
  ];

  // Insights (주간 발행, weekly)
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

  // Dynamic: companies
  let companyRoutes: MetadataRoute.Sitemap = [];
  try {
    const rows = await fetchActiveCompaniesForSitemap(5000);
    companyRoutes = rows
      .filter((r) => /^\d{10}$/.test(r.bizrno_norm))
      .map((r) => ({
        url: `${BASE_URL}/companies/${r.bizrno_norm}`,
        lastModified: r.updated_at ? new Date(r.updated_at) : now,
        changeFrequency: "weekly" as const,
        priority: 0.6,
      }));
  } catch {
    // 시드 데이터 부족 시 빈 list. 검색엔진은 정적 routes만 인덱싱.
  }

  // Dynamic: notices (라이프사이클 페이지)
  let noticeRoutes: MetadataRoute.Sitemap = [];
  try {
    const rows = await fetchRecentNoticesForSitemap(3000);
    noticeRoutes = rows
      .filter((r) => r.bid_ntce_no)
      .map((r) => ({
        url: `${BASE_URL}/notices/${r.bid_ntce_no}`,
        lastModified: r.updated_at ? new Date(r.updated_at) : now,
        changeFrequency: "weekly" as const,
        priority: 0.5,
      }));
  } catch {
    // 데이터 없으면 skip
  }

  return [...staticRoutes, ...insightRoutes, ...companyRoutes, ...noticeRoutes];
}
