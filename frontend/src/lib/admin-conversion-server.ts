import "server-only";
import { countConversions, type Conversions, type ConversionEvent } from "./admin-conversion";

/** DB 집계와 섞지 않고 같은 계측의 세션으로 전환을 비교한다. 키/조회 실패는 0으로 위장하지 않는다. */
export async function fetchConversions(todayKst: string): Promise<Conversions> {
  const empty: Conversions = { today: countConversions([], 0), week: countConversions([], 0), error: null, truncated: false };
  const key = process.env.POSTHOG_PERSONAL_API_KEY;
  const project = process.env.POSTHOG_PROJECT_ID;
  if (!key || !project) return { ...empty, error: "PostHog 조회 키 미설정" };
  const today = Date.parse(`${todayKst}T00:00:00+09:00`);
  const week = today - 6 * 86_400_000;
  const since = new Date(week).toISOString().slice(0, 19).replace("T", " ");
  const host = (process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com")
    .replace(/\/\/(\w+)\.i\.posthog\.com/, "//$1.posthog.com").replace(/\/$/, "");
  try {
    const response = await fetch(`${host}/api/projects/${project}/query`, {
      method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      cache: "no-store", signal: AbortSignal.timeout(10_000),
      body: JSON.stringify({ query: { kind: "HogQLQuery", query: `
        SELECT properties.jf_session_id, event, toString(timestamp), properties.logged_in
        FROM events
        WHERE timestamp >= toDateTime('${since}', 'UTC')
          AND event IN ('results_view', 'notice_click', 'notice_save_intent', 'notice_save', 'signup_view')
          AND notEmpty(toString(properties.jf_session_id))
          AND properties.$host IN ('jodalfit.co.kr', 'www.jodalfit.co.kr')
        ORDER BY timestamp ASC LIMIT 10001
      ` } }),
    });
    if (!response.ok) throw new Error(`PostHog ${response.status}`);
    const data = await response.json() as { results?: [string, string, string, number | null][] };
    if (!Array.isArray(data.results)) throw new Error("PostHog 응답 형식 오류");
    const events: ConversionEvent[] = data.results.slice(0, 10000).map(([session, event, at, loggedIn]) => ({
      session, event, at: at.replace(" ", "T") + (/Z$|[+-]\d\d:\d\d$/.test(at) ? "" : "Z"),
      loggedIn: loggedIn == null ? null : Number(loggedIn) === 1,
    }));
    return { today: countConversions(events, today), week: countConversions(events, week), error: null, truncated: data.results.length > 10000 };
  } catch (e) { return { ...empty, error: e instanceof Error ? e.message : String(e) }; }
}
