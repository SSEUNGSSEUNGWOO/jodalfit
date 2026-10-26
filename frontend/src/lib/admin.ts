// frontend/src/lib/admin.ts
// /admin 이 읽는 운영 숫자 — 전부 읽기 전용, service_role 로 서버에서만. 쓰기(사용자 삭제·비공개 처리)는 두지 않는다 —
// 사용자가 2명일 때 그건 Supabase 대시보드가 더 안전하다(2026-10-26 결정).
// 실사용 지표 규칙(CLAUDE.md "로그 지표"): search_logs 는 source = 'user' 만, notice_events 는 internal 을 뺀다.
// 방문(페이지뷰·방문자·유입)은 서버 로그가 없다 — PostHog 쿼리 API(개인 키 POSTHOG_PERSONAL_API_KEY + POSTHOG_PROJECT_ID). 키가 없으면 그 판만 비운다.
import "server-only";
import { getServerSupabase } from "@/lib/supabase-server";
import { kstDate } from "@/lib/format";

/** 관리자 — 환경변수 ADMIN_EMAILS(쉼표 구분). 비어 있으면 아무도 아니다(운영에서 빠뜨려도 열리지 않는다). */
export function isAdmin(email: string | null | undefined): boolean {
  if (!email) return false;
  const list = (process.env.ADMIN_EMAILS ?? "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  return list.includes(email.toLowerCase());
}

/** ab***@domain — 화면에 원문 메일을 내리지 않는다(관리자 본인만 보지만 스크린샷·공유에 대비). */
export function maskEmail(email: string | null | undefined): string {
  if (!email || !email.includes("@")) return "—";
  const [local, domain] = email.split("@");
  return `${local.slice(0, 2)}***@${domain}`;
}

export type SearchRow = {
  at: string; mode: string; query: string; matched: string | null; matchedBizrno: string | null;
  results: number | null; error: boolean; ip: string; referer: string | null;
};
export type UserRow = { id: string; email: string; createdAt: string; lastSignInAt: string | null; confirmed: boolean; saved: number; reviewed: number };
export type SavedRow = { at: string; user: string; bizrnoNorm: string; name: string };
export type ReviewedRow = { at: string; user: string; bidNtceNo: string; title: string };
export type FeedbackRow = { id: number; at: string; kind: "idea" | "question" | "bug"; message: string; email: string | null; page: string | null; handled: boolean };
export type Funnel = { searches: number; visitors: number; identified: number; clicks: number; signups: number; saved: number; reviewed: number };
export type Health = { errorRate: number | null; zeroRate: number | null; p50: number | null };   // 비율은 0~1, p50 은 ms. 검색 0건이면 null
export type Visits = {
  daily: { date: string; views: number; visitors: number }[];                 // 오늘 포함 7일, KST
  byType: { type: string; views: number; visitors: number }[];               // 7일
  referrers: { domain: string; views: number; visitors: number }[];          // 7일, 많은 순
  error: string | null;                                                       // 키 없음·API 실패 — 판에 한 줄로
};

export type AdminData = {
  todayKst: string;
  today: Funnel;
  week: Funnel;
  daily: ({ date: string } & Funnel)[];   // 오늘 포함 7일, 최신 먼저
  health: { today: Health; week: Health };
  zeroQueries: SearchRow[];              // 7일, 결과 0건(오류 제외), 최신순
  visits: Visits;
  feedback: FeedbackRow[];               // 최근 50, 최신순 (0061)
  users: UserRow[];
  searches: SearchRow[];                 // 최근 7일, 최신순, 최대 200
  savedRows: SavedRow[];
  reviewedRows: ReviewedRow[];
};

type LogRow = { created_at: string; query: string | null; mode: string | null; matched_corp_nm: string | null; matched_bizrno: string | null; result_count: number | null; has_error: boolean | null; ip_hash: string | null; referer: string | null; latency_ms: number | null };
type EventRow = { created_at: string; event_type: string; source: string | null };
type SavedKey = { user_id: string; bizrno_norm: string; created_at: string };
type ReviewedKey = { user_id: string; bid_ntce_no: string; bid_ntce_ord: string; created_at: string };

/** 검색 요청의 referer = 검색이 일어난 우리 페이지. 외부 유입(네이버 등)이 아니다 — 그건 방문 판(PostHog)에 있다.
 *  우리 도메인이면 경로만("/" 는 홈), 다른 도메인이면 호스트(임베드·프록시 같은 예외 상황). */
function refererPage(r: string | null): string | null {
  if (!r) return null;
  try {
    const u = new URL(r);
    if (u.host.endsWith("jodalfit.co.kr")) return u.pathname === "/" ? "홈" : u.pathname.replace(/\/$/, "");
    return u.host.replace(/^www\./, "");
  } catch {
    return r.slice(0, 40);
  }
}

function p50(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.floor((s.length - 1) / 2)];
}

function toRow(r: LogRow): SearchRow {
  return {
    at: r.created_at, mode: r.mode ?? "—", query: r.query ?? "", matched: r.matched_corp_nm, matchedBizrno: r.matched_bizrno,
    results: r.result_count, error: !!r.has_error, ip: (r.ip_hash ?? "").slice(0, 4), referer: refererPage(r.referer),
  };
}

/** PostHog HogQL — 개인 API 키(phx_…)로 프로젝트 쿼리. 수집 호스트(us.i.posthog.com)와 API 호스트(us.posthog.com)가 다르다. */
async function fetchVisits(todayKst: string): Promise<Visits> {
  const key = process.env.POSTHOG_PERSONAL_API_KEY;
  const project = process.env.POSTHOG_PROJECT_ID;
  const empty: Visits = { daily: [], byType: [], referrers: [], error: null };
  if (!key || !project) return { ...empty, error: "POSTHOG_PERSONAL_API_KEY · POSTHOG_PROJECT_ID 미설정" };
  const ingest = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";
  const api = ingest.replace(/\/\/(\w+)\.i\.posthog\.com/, "//$1.posthog.com").replace(/\/$/, "");
  // 하한은 UTC 문자열로(KST 자정 − 6일). HogQL 의 toDate 는 인자 하나라 날짜 묶기는 toTimeZone 으로(2026-10-26 확인)
  const sinceUtc = new Date(new Date(`${todayKst}T00:00:00+09:00`).getTime() - 6 * 86_400_000).toISOString().slice(0, 19).replace("T", " ");
  const base = `FROM events WHERE event = '$pageview' AND timestamp >= toDateTime('${sinceUtc}', 'UTC')`;
  const q = async <T,>(query: string): Promise<T[]> => {
    const res = await fetch(`${api}/api/projects/${project}/query`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ query: { kind: "HogQLQuery", query } }),
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`PostHog ${res.status}`);
    const j = (await res.json()) as { results: unknown[][] };
    return j.results as T[];
  };
  try {
    const [daily, byType, refs] = await Promise.all([
      q<[string, number, number]>(`SELECT toString(toDate(toTimeZone(timestamp, 'Asia/Seoul'))) AS d, count() AS v, count(DISTINCT person_id) AS u ${base} GROUP BY d ORDER BY d DESC`),
      q<[string, number, number]>(`SELECT multiIf(properties.$pathname = '/', 'home', properties.$pathname LIKE '/companies/%', 'company', properties.$pathname = '/companies', 'companies', properties.$pathname LIKE '/notices/%', 'notice', properties.$pathname = '/notices', 'notices', properties.$pathname LIKE '/recommendations%', 'results', properties.$pathname LIKE '/saved%', 'saved', startsWith(properties.$pathname, '/login') OR startsWith(properties.$pathname, '/signup') OR startsWith(properties.$pathname, '/reset'), 'auth', 'other') AS t, count() AS v, count(DISTINCT person_id) AS u ${base} GROUP BY t ORDER BY v DESC`),
      q<[string | null, number, number]>(`SELECT coalesce(nullIf(properties.$referring_domain, ''), '$direct') AS r, count() AS v, count(DISTINCT person_id) AS u ${base} GROUP BY r ORDER BY v DESC LIMIT 10`),
    ]);
    return {
      daily: daily.map(([date, views, visitors]) => ({ date, views, visitors })),
      byType: byType.map(([type, views, visitors]) => ({ type, views, visitors })),
      referrers: refs.map(([domain, views, visitors]) => ({ domain: domain ?? "$direct", views, visitors })),
      error: null,
    };
  } catch (e) {
    return { ...empty, error: e instanceof Error ? e.message : String(e) };
  }
}

export async function fetchAdminData(now: Date = new Date()): Promise<AdminData> {
  const sb = getServerSupabase();
  const todayKst = kstDate(now);
  const todayStart = new Date(`${todayKst}T00:00:00+09:00`);
  const weekStart = new Date(todayStart.getTime() - 6 * 86_400_000);
  const since = weekStart.toISOString();

  const [logs, events, usersRes, saved, reviewed, visits, fb] = await Promise.all([
    sb.from("search_logs")
      .select("created_at,query,mode,matched_corp_nm,matched_bizrno,result_count,has_error,ip_hash,referer,latency_ms")
      .gte("created_at", since).eq("source", "user").order("created_at", { ascending: false }).limit(1000),
    sb.from("notice_events").select("created_at,event_type,source")
      .gte("created_at", since).eq("event_type", "click").neq("source", "internal").limit(5000),
    sb.auth.admin.listUsers({ page: 1, perPage: 200 }),
    sb.from("saved_companies").select("user_id,bizrno_norm,created_at").order("created_at", { ascending: false }).limit(200),
    sb.from("reviewed_notices").select("user_id,bid_ntce_no,bid_ntce_ord,created_at").order("created_at", { ascending: false }).limit(200),
    fetchVisits(todayKst),
    sb.from("feedback").select("id,created_at,kind,message,email,page,handled_at").order("created_at", { ascending: false }).limit(50),
  ]);

  // 로컬 개발 서버(check_*.py 검증)도 운영 DB 에 source='user' 로 남는다 — referer 가 localhost 면 사람이 아니다(2026-10-26 화면에서 확인)
  const logRows = ((logs.data ?? []) as LogRow[]).filter((r) => !/^https?:\/\/(localhost|127\.0\.0\.1)/.test(r.referer ?? ""));
  const clickRows = ((events.data ?? []) as EventRow[]).filter((e) => e.source !== "bot");
  const users = usersRes.data?.users ?? [];
  const savedRows = (saved.data ?? []) as SavedKey[];
  const reviewedRows = (reviewed.data ?? []) as ReviewedKey[];

  // 회사명·공고명은 공개 테이블에서 한 번에
  const norms = [...new Set(savedRows.map((r) => r.bizrno_norm))];
  const nos = [...new Set(reviewedRows.map((r) => r.bid_ntce_no))];
  const [cos, nts] = await Promise.all([
    norms.length ? sb.from("companies").select("bizrno_norm,corp_nm").in("bizrno_norm", norms).order("embedded_at", { ascending: false, nullsFirst: false }) : Promise.resolve({ data: [] as { bizrno_norm: string; corp_nm: string }[] }),
    nos.length ? sb.from("bid_notices").select("bid_ntce_no,bid_ntce_nm").in("bid_ntce_no", nos) : Promise.resolve({ data: [] as { bid_ntce_no: string; bid_ntce_nm: string }[] }),
  ]);
  const nameOf = new Map<string, string>();
  for (const c of (cos.data ?? []) as { bizrno_norm: string; corp_nm: string }[]) if (!nameOf.has(c.bizrno_norm)) nameOf.set(c.bizrno_norm, c.corp_nm);
  const titleOf = new Map<string, string>();
  for (const n of (nts.data ?? []) as { bid_ntce_no: string; bid_ntce_nm: string }[]) if (!titleOf.has(n.bid_ntce_no)) titleOf.set(n.bid_ntce_no, n.bid_ntce_nm);
  const emailOf = new Map(users.map((u) => [u.id, maskEmail(u.email)]));

  const funnel = (from: Date, to?: Date): Funnel => {
    const t0 = from.getTime(), t1 = to?.getTime() ?? Infinity;
    const inRange = (s: string) => { const t = Date.parse(s); return t >= t0 && t < t1; };
    const L = logRows.filter((r) => inRange(r.created_at));
    return {
      searches: L.length,
      visitors: new Set(L.map((r) => r.ip_hash).filter(Boolean)).size,
      identified: L.filter((r) => r.mode === "company" && r.matched_bizrno).length,
      clicks: clickRows.filter((e) => inRange(e.created_at)).length,
      signups: users.filter((u) => u.created_at && inRange(u.created_at)).length,
      saved: savedRows.filter((r) => inRange(r.created_at)).length,
      reviewed: reviewedRows.filter((r) => inRange(r.created_at)).length,
    };
  };
  const health = (from: Date): Health => {
    const L = logRows.filter((r) => Date.parse(r.created_at) >= from.getTime());
    if (L.length === 0) return { errorRate: null, zeroRate: null, p50: null };
    return {
      errorRate: L.filter((r) => r.has_error).length / L.length,
      zeroRate: L.filter((r) => !r.has_error && r.result_count === 0).length / L.length,
      p50: p50(L.map((r) => r.latency_ms).filter((v): v is number => typeof v === "number")),
    };
  };
  const daily = Array.from({ length: 7 }, (_, i) => {
    const from = new Date(todayStart.getTime() - i * 86_400_000);
    return { date: kstDate(from), ...funnel(from, new Date(from.getTime() + 86_400_000)) };
  });

  return {
    todayKst,
    today: funnel(todayStart),
    week: funnel(weekStart),
    daily,
    health: { today: health(todayStart), week: health(weekStart) },
    zeroQueries: logRows.filter((r) => !r.has_error && r.result_count === 0).slice(0, 50).map(toRow),
    visits,
    feedback: ((fb.data ?? []) as { id: number; created_at: string; kind: FeedbackRow["kind"]; message: string; email: string | null; page: string | null; handled_at: string | null }[])
      .map((r) => ({ id: r.id, at: r.created_at, kind: r.kind, message: r.message, email: r.email, page: r.page, handled: !!r.handled_at })),
    users: users
      .slice()
      .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      .map((u) => ({
        id: u.id, email: maskEmail(u.email), createdAt: u.created_at, lastSignInAt: u.last_sign_in_at ?? null,
        confirmed: !!u.email_confirmed_at,
        saved: savedRows.filter((r) => r.user_id === u.id).length,
        reviewed: reviewedRows.filter((r) => r.user_id === u.id).length,
      })),
    searches: logRows.slice(0, 200).map(toRow),
    savedRows: savedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bizrnoNorm: r.bizrno_norm, name: nameOf.get(r.bizrno_norm) ?? r.bizrno_norm })),
    reviewedRows: reviewedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bidNtceNo: r.bid_ntce_no, title: titleOf.get(r.bid_ntce_no) ?? r.bid_ntce_no })),
  };
}
