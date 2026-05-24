import type { MetadataRoute } from "next";
import { fetchActiveCompaniesForSitemap } from "@/lib/company";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://jodalfit.co.kr";

export const revalidate = 86400; // 1 day

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
  ];

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

  return [...staticRoutes, ...companyRoutes];
}
