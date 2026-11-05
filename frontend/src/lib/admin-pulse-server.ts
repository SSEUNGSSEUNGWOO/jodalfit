import "server-only";
import { unstable_cache } from "next/cache";
import type { Pulse } from "./admin-summary";

const empty: Pulse = { visitors: 0, previousVisitors: 0, views: 0, previousViews: 0, returning: 0, searchers: 0, resultViewers: 0, outboundUsers: 0, outboundClicks: 0, error: null };

/** 익명 방문 집계만 5분 재사용한다. 관리자 권한 검사는 호출 페이지에서 먼저 수행한다. */
const readPulse = unstable_cache(async (todayKst: string): Promise<Pulse> => {
  const key = process.env.POSTHOG_PERSONAL_API_KEY, project = process.env.POSTHOG_PROJECT_ID;
  if (!key || !project) throw new Error("PostHog 조회 키 미설정");
  const until = Date.parse(`${todayKst}T00:00:00+09:00`);
  const sqlDate = (offset: number) => new Date(until - offset * 86_400_000).toISOString().slice(0, 19).replace("T", " ");
  const middle = `toDateTime('${sqlDate(7)}', 'UTC')`;
  const host = (process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com").replace(/\/\/(\w+)\.i\.posthog\.com/, "//$1.posthog.com").replace(/\/$/, "");
  const query = `SELECT countIf(previous_views > 0), countIf(current_views > 0), sum(previous_views), sum(current_views),
    countIf(previous_views > 0 AND current_views > 0), countIf(searches > 0), countIf(results > 0), countIf(outbound > 0), sum(outbound)
    FROM (SELECT distinct_id,
      countIf(event = '$pageview' AND timestamp < ${middle}) AS previous_views,
      countIf(event = '$pageview' AND timestamp >= ${middle}) AS current_views,
      countIf(event = 'search_submit' AND timestamp >= ${middle}) AS searches,
      countIf(event = 'results_view' AND timestamp >= ${middle}) AS results,
      countIf(event = 'g2b_outbound' AND timestamp >= ${middle}) AS outbound
      FROM events WHERE timestamp >= toDateTime('${sqlDate(14)}', 'UTC') AND timestamp < toDateTime('${sqlDate(0)}', 'UTC')
        AND event IN ('$pageview', 'search_submit', 'results_view', 'g2b_outbound')
        AND (properties.$current_url LIKE 'https://jodalfit.co.kr/%' OR properties.$current_url LIKE 'https://www.jodalfit.co.kr/%')
        AND NOT startsWith(coalesce(properties.$pathname, ''), '/admin') AND NOT startsWith(coalesce(properties.$pathname, ''), '/dev/')
      GROUP BY distinct_id)`;
  const response = await fetch(`${host}/api/projects/${project}/query`, {
    method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query: { kind: "HogQLQuery", query } }), cache: "no-store", signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`PostHog ${response.status}`);
  const body = await response.json() as { results?: unknown[][] };
  const row = body.results?.[0];
  if (!row || row.length !== 9 || row.some((n) => n == null || !Number.isFinite(Number(n)))) throw new Error("PostHog 집계 응답 오류");
  const [previousVisitors, visitors, previousViews, views, returning, searchers, resultViewers, outboundUsers, outboundClicks] = row.map(Number);
  return { previousVisitors, visitors, previousViews, views, returning, searchers, resultViewers, outboundUsers, outboundClicks, error: null };
}, ["admin-service-pulse-v1"], { revalidate: 300 });

export async function fetchAdminPulse(todayKst: string): Promise<Pulse> {
  try { return await readPulse(todayKst); }
  catch (e) { return { ...empty, error: e instanceof Error ? e.message : "방문 집계 조회 실패" }; }
}
