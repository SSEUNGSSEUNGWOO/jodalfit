import { getServerSupabase } from "@/lib/supabase-server";

export type SitemapKind = "company" | "notice";

export interface SitemapUrlRow {
  path: string;
  lastmod: string | null;
}

/**
 * 사이트맵 URL 창(window) 조회 — materialized view `sitemap_urls` (migration 0026).
 *
 * 매 요청 companies/bid_notices 를 직접 훑던 방식은 Disk IO 소진 시 페이지당 40초를 넘겨
 * 실패했고, 그 오류를 삼켜 빈 200 사이트맵을 내보내는 바람에 구글 색인이 끊겼다 (2026-07~09).
 * 여기서는 오류를 반드시 던진다 — 5xx 를 받은 크롤러는 기존 색인을 유지하고 재시도하지만,
 * 빈 200 은 "URL 0개 사이트맵"으로 학습한다.
 */
export async function fetchSitemapUrls(
  kind: SitemapKind,
  offset: number,
  limit: number
): Promise<SitemapUrlRow[]> {
  const c = getServerSupabase();
  const out: SitemapUrlRow[] = [];
  // PostgREST max_rows(1000)에 맞춰 seq 창을 1000개씩 끊어 받는다.
  const PAGE = 1000;
  const end = offset + limit;
  for (let from = offset; from < end; from += PAGE) {
    const to = Math.min(from + PAGE, end);
    const { data, error } = await c
      .from("sitemap_urls")
      .select("path,lastmod")
      .eq("kind", kind)
      .gte("seq", from)
      .lt("seq", to)
      .order("seq", { ascending: true });
    if (error) {
      throw new Error(`sitemap_urls ${kind} seq ${from}-${to}: ${error.message}`);
    }
    if (!data?.length) break;
    out.push(...(data as SitemapUrlRow[]));
    if (data.length < to - from) break;
  }
  return out;
}
