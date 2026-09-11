import type { MetadataRoute } from "next";
import { fetchSitemapUrls } from "@/lib/sitemap-urls";
import { fetchIndustryDirectory } from "@/lib/industry";
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

  // 회사·공고 URL은 materialized view `sitemap_urls`(migration 0026)에서 읽는다.
  // 원본 테이블을 매 요청 훑던 방식은 Disk IO 소진 시 40초를 넘겨 실패했고,
  // 오류를 삼켜 빈 200을 내보낸 탓에 구글 색인이 끊겼다 (2026-07~09).
  // fetchSitemapUrls 는 오류를 던진다 — 5xx 를 받은 크롤러는 기존 색인을 유지한다.

  // 0 ~ COMPANY_SEGMENTS-1: 회사. 색인 대상이 5만 URL 한도를 넘어 나눠 싣는다.
  if (segment < COMPANY_SEGMENTS) {
    const rows = await fetchSitemapUrls(
      "company",
      segment * PER_SEGMENT,
      PER_SEGMENT
    );
    return rows.map((r) => ({
      url: `${BASE_URL}${r.path}`,
      lastModified: r.lastmod ? new Date(r.lastmod) : STATIC_LASTMOD,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    }));
  }

  // 공고 (라이프사이클 페이지) — 최신 PER_SEGMENT 건
  if (segment === NOTICE_SEGMENT_ID) {
    const rows = await fetchSitemapUrls("notice", 0, PER_SEGMENT);
    return rows.map((r) => ({
      url: `${BASE_URL}${r.path}`,
      lastModified: r.lastmod ? new Date(r.lastmod) : STATIC_LASTMOD,
      changeFrequency: "weekly" as const,
      priority: 0.5,
    }));
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
    {
      url: `${BASE_URL}/companies/industry`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "weekly",
      priority: 0.8,
    },
  ];

  // 업종별 집계 페이지 1페이지 (migration 0027 MV). 2페이지 이후는 페이지네이션 링크로 닿는다.
  // MV 미적용 환경에서도 나머지 세그먼트가 살도록 실패는 삼킨다 (수백 URL 규모라 빈 200 위험과 무관).
  let industryRoutes: MetadataRoute.Sitemap = [];
  try {
    const industries = await fetchIndustryDirectory();
    industryRoutes = industries.map((i) => ({
      url: `${BASE_URL}/companies/industry/${i.indstryty_cd}/1`,
      lastModified: STATIC_LASTMOD,
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));
  } catch {
    // industry_directory 없으면 skip
  }

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

  return [...staticRoutes, ...industryRoutes, ...insightRoutes];
}
