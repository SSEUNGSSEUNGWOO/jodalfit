// frontend/src/lib/admin.ts
// /admin 이 읽는 운영 숫자 — 전부 읽기 전용, service_role 로 서버에서만. 쓰기(사용자 삭제·비공개 처리)는 두지 않는다 —
// 사용자가 2명일 때 그건 Supabase 대시보드가 더 안전하다(2026-10-26 결정).
// 실사용 지표 규칙(CLAUDE.md "로그 지표"): search_logs 는 source = 'user' 만, notice_events 는 internal 을 뺀다.
// 방문(페이지뷰·방문자·유입)은 서버 로그가 없다 — PostHog 쿼리 API(개인 키 POSTHOG_PERSONAL_API_KEY + POSTHOG_PROJECT_ID). 키가 없으면 그 판만 비운다.
import "server-only";
import { getServerSupabase } from "@/lib/supabase-server";
import { kstDate } from "@/lib/format";
import { fetchConversions } from "./admin-conversion-server";
import type { Conversions } from "./admin-conversion";
import type { User } from "@supabase/supabase-js";
import { fetchAdminPulse } from "./admin-pulse-server";
import { fallbackKeys, isExcludedMember, readAdminRows, searchKey, summarizeMembers, summarizeSearches, type AdminOverview } from "./admin-summary";

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
  results: number | null; error: boolean; errorMsg: string | null; ip: string; referer: string | null;
  fallback: boolean; // 회사를 못 찾았지만 화면이 키워드로 넘겨 결과를 본 검색(admin-summary.fallbackKeys) — 막힌 검색이 아니다
};
export type UserRow = { id: string; email: string; createdAt: string; lastSignInAt: string | null; confirmed: boolean; saved: number; reviewed: number };
export type SavedRow = { at: string; user: string; bizrnoNorm: string; name: string };
export type ReviewedRow = { at: string; user: string; bidNtceNo: string; title: string };
export type FeedbackRow = { id: number; at: string; kind: "idea" | "question" | "bug"; message: string; email: string | null; page: string | null; handled: boolean };
export type Funnel = { searches: number; visitors: number; identified: number; clicks: number; signups: number; saved: number; reviewed: number };
export type Health = { errorRate: number | null; zeroRate: number | null; p50: number | null; helpful: number | null; helpfulN: number | null };   // 비율은 0~1, p50 은 ms. 검색 0건이면 null. helpful = "도움이 됐습니까" 예 비율, helpfulN = 응답 수(0063)
export type Visits = {
  daily: { date: string; views: number; visitors: number }[];                 // 오늘 포함 7일, KST
  byType: { type: string; views: number; visitors: number }[];               // 7일
  referrers: { domain: string; views: number; visitors: number }[];          // 7일, 많은 순
  error: string | null;                                                       // 키 없음·API 실패 — 판에 한 줄로
};

/** 미출시 기능 수요 조사(0068 feature_interest, 최근 30일). views = 버튼이 화면에 들어온 수(봇 제외) — 클릭률의 분모.
 *  registers = 클릭 전부, registeredUsers = 로그인 상태로 등록한 고유 회원, anonRegisters = 비로그인 클릭(가입 완료 여부와 별도).
 *  byDiv 는 관심 공고의 업무구분 — 클릭 수만 보면 노출이 많은 구분이 커 보이므로 노출과 같이 둔다. */
export type Interest = { views: number; registers: number; registeredUsers: number; anonRegisters: number; byDiv: { div: string; views: number; registers: number }[]; error: string | null };

export type AdminData = {
  todayKst: string;
  overview: AdminOverview;
  today: Funnel;
  week: Funnel;
  daily: ({ date: string } & Funnel)[];   // 오늘 포함 7일, 최신 먼저
  health: { today: Health; week: Health };
  zeroQueries: SearchRow[];              // 7일, 결과 0건(오류 제외), 최신순
  problemQueries: SearchRow[];
  visits: Visits;
  conversions: Conversions;
  feedback: FeedbackRow[];               // 최근 50, 최신순 (0061)
  interest: Interest;                    // 제안서 작성 준비안 관심 등록, 최근 30일 (0068)
  users: UserRow[];
  searches: SearchRow[];                 // 최근 7일, 최신순, 최대 200
  savedRows: SavedRow[];
  reviewedRows: ReviewedRow[];
};

type LogRow = { created_at: string; query: string | null; mode: string | null; matched_corp_nm: string | null; matched_bizrno: string | null; result_count: number | null; has_error: boolean | null; error_msg: string | null; ip_hash: string | null; referer: string | null; latency_ms: number | null };
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

function toRow(r: LogRow, fallback?: Set<string>): SearchRow {
  return {
    at: r.created_at, mode: r.mode ?? "—", query: r.query ?? "", matched: r.matched_corp_nm, matchedBizrno: r.matched_bizrno,
    results: r.result_count, error: !!r.has_error, errorMsg: r.error_msg, ip: (r.ip_hash ?? "").slice(0, 4), referer: refererPage(r.referer),
    fallback: !!fallback?.has(searchKey(r)),
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
  const base = `FROM events WHERE event = '$pageview' AND timestamp >= toDateTime('${sinceUtc}', 'UTC')
    AND (properties.$current_url LIKE 'https://jodalfit.co.kr/%' OR properties.$current_url LIKE 'https://www.jodalfit.co.kr/%')
    AND NOT startsWith(coalesce(properties.$pathname, ''), '/admin') AND NOT startsWith(coalesce(properties.$pathname, ''), '/dev/')`;
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
      q<[string, number, number]>(`SELECT toString(toDate(toTimeZone(timestamp, 'Asia/Seoul'))) AS d, count() AS v, count(DISTINCT distinct_id) AS u ${base} GROUP BY d ORDER BY d DESC`),
      q<[string, number, number]>(`SELECT multiIf(properties.$pathname = '/', 'home', properties.$pathname LIKE '/companies/%', 'company', properties.$pathname = '/companies', 'companies', properties.$pathname LIKE '/notices/%', 'notice', properties.$pathname = '/notices', 'notices', properties.$pathname LIKE '/recommendations%', 'results', properties.$pathname LIKE '/saved%', 'saved', startsWith(properties.$pathname, '/login') OR startsWith(properties.$pathname, '/signup') OR startsWith(properties.$pathname, '/reset'), 'auth', 'other') AS t, count() AS v, count(DISTINCT distinct_id) AS u ${base} GROUP BY t ORDER BY v DESC`),
      q<[string | null, number, number]>(`SELECT coalesce(nullIf(properties.$referring_domain, ''), '$direct') AS r, count() AS v, count(DISTINCT distinct_id) AS u ${base} GROUP BY r ORDER BY v DESC LIMIT 10`),
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
  const completeStart = new Date(todayStart.getTime() - 7 * 86_400_000);
  const since = completeStart.toISOString(); // 완료된 7일 + 오늘. 상세 판은 아래에서 기간을 좁힌다.

  const since30 = new Date(todayStart.getTime() - 29 * 86_400_000).toISOString();
  const [logs, events, usersRes, saved, reviewed, visits, fb, helpfulRes, conversions, interestRes, pulse] = await Promise.all([
    readAdminRows<LogRow>((from, to) => sb.from("search_logs")
      .select("created_at,query,mode,matched_corp_nm,matched_bizrno,result_count,has_error,error_msg,ip_hash,referer,latency_ms")
      .gte("created_at", since).eq("source", "user").order("created_at", { ascending: false }).order("id", { ascending: false }).range(from, to)),
    readAdminRows<EventRow>((from, to) => sb.from("notice_events").select("created_at,event_type,source")
      .gte("created_at", since).eq("event_type", "click").eq("source", "user").order("created_at", { ascending: false }).order("id", { ascending: false }).range(from, to)),
    readAdminRows<User>(async (from) => { const r = await sb.auth.admin.listUsers({ page: Math.floor(from / 200) + 1, perPage: 200 }); return { data: r.data?.users ?? null, error: r.error }; }, 200, 2000),
    readAdminRows<SavedKey>((from, to) => sb.from("saved_companies").select("user_id,bizrno_norm,created_at").order("created_at", { ascending: false }).order("user_id").order("bizrno_norm").range(from, to)),
    readAdminRows<ReviewedKey>((from, to) => sb.from("reviewed_notices").select("user_id,bid_ntce_no,bid_ntce_ord,created_at").order("created_at", { ascending: false }).order("user_id").order("bid_ntce_no").order("bid_ntce_ord").range(from, to)),
    fetchVisits(todayKst),
    sb.from("feedback").select("id,created_at,kind,message,email,page,handled_at").order("created_at", { ascending: false }).limit(50),
    readAdminRows<{ created_at: string; helpful: boolean }>((from, to) => sb.from("result_feedback").select("created_at,helpful").gte("created_at", since).eq("source", "user").order("created_at", { ascending: false }).order("id", { ascending: false }).range(from, to)),
    fetchConversions(todayKst),
    readAdminRows<{ event: "view" | "register"; bid_ntce_no: string; user_id: string | null }>((from, to) => sb.from("feature_interest").select("event,bid_ntce_no,user_id").eq("feature", "proposal_prep").gte("created_at", since30).order("created_at", { ascending: false }).order("id", { ascending: false }).range(from, to)),
    fetchAdminPulse(todayKst),
  ]);
  const helpfulRows = (helpfulRes.data ?? []) as { created_at: string; helpful: boolean }[];
  const rawInterestRows = interestRes.data;

  // 로컬 개발 서버(check_*.py 검증)도 운영 DB 에 source='user' 로 남는다 — referer 가 localhost 면 사람이 아니다(2026-10-26 화면에서 확인)
  const logRows = ((logs.data ?? []) as LogRow[]).filter((r) => !/^https?:\/\/(localhost|127\.0\.0\.1)/.test(r.referer ?? ""));
  const clickRows = ((events.data ?? []) as EventRow[]).filter((e) => e.source !== "bot");
  const allUsers = usersRes.data;
  const excludedEmails = [...(process.env.ADMIN_EMAILS ?? "").split(","), ...(process.env.ADMIN_EXCLUDE_EMAILS ?? "").split(",")].map((s) => s.trim().toLowerCase()).filter(Boolean);
  const users = allUsers.filter((u) => !isExcludedMember(u.email, excludedEmails));
  const userIds = new Set(users.map((u) => u.id));
  const interestRows = rawInterestRows.filter((r) => !r.user_id || userIds.has(r.user_id));
  const savedRows = saved.data.filter((r) => userIds.has(r.user_id));
  const reviewedRows = reviewed.data.filter((r) => userIds.has(r.user_id));
  const issues = [
    ...([["검색", logs], ["공고 행동", events], ["회원", usersRes], ["회사 저장", saved], ["공고 저장", reviewed], ["추천 도움 응답", helpfulRes], ["기능 관심", interestRes]] as const)
      .flatMap(([name, r]) => r.error ? [`${name} 조회 실패`] : r.truncated ? [`${name} 조회 상한 도달 — 일부 기록 기준`] : []),
    ...(fb.error ? ["의견·문의 조회 실패"] : []),
  ];

  // 회사명·공고명은 공개 테이블에서 한 번에
  const norms = [...new Set(savedRows.map((r) => r.bizrno_norm))];
  const nos = [...new Set(reviewedRows.map((r) => r.bid_ntce_no))];
  const interestNos = [...new Set(interestRows.map((r) => r.bid_ntce_no))];
  const [cos, nts, intNts] = await Promise.all([
    norms.length ? sb.from("companies").select("bizrno_norm,corp_nm").in("bizrno_norm", norms).order("embedded_at", { ascending: false, nullsFirst: false }) : Promise.resolve({ data: [] as { bizrno_norm: string; corp_nm: string }[] }),
    nos.length ? sb.from("bid_notices").select("bid_ntce_no,bid_ntce_nm").in("bid_ntce_no", nos) : Promise.resolve({ data: [] as { bid_ntce_no: string; bid_ntce_nm: string }[] }),
    interestNos.length ? sb.from("bid_notices").select("bid_ntce_no,bsns_div_nm").in("bid_ntce_no", interestNos) : Promise.resolve({ data: [] as { bid_ntce_no: string; bsns_div_nm: string | null }[] }),
  ]);
  const divOf = new Map<string, string>();
  for (const n of (intNts.data ?? []) as { bid_ntce_no: string; bsns_div_nm: string | null }[]) if (!divOf.has(n.bid_ntce_no)) divOf.set(n.bid_ntce_no, n.bsns_div_nm || "—");
  const byDivMap = new Map<string, { views: number; registers: number }>();
  for (const r of interestRows) {
    const d = divOf.get(r.bid_ntce_no) ?? "—";
    const acc = byDivMap.get(d) ?? { views: 0, registers: 0 };
    if (r.event === "view") acc.views += 1; else acc.registers += 1;
    byDivMap.set(d, acc);
  }
  const interest: Interest = {
    views: interestRows.filter((r) => r.event === "view").length,
    registers: interestRows.filter((r) => r.event === "register").length,
    registeredUsers: new Set(interestRows.filter((r) => r.event === "register" && r.user_id).map((r) => r.user_id)).size,
    anonRegisters: interestRows.filter((r) => r.event === "register" && !r.user_id).length,
    byDiv: [...byDivMap.entries()].map(([div, v]) => ({ div, ...v })).sort((a, b) => b.registers - a.registers || b.views - a.views),
    error: interestRes.error || usersRes.error || interestRes.truncated || usersRes.truncated ? "기능 관심 조회 실패" : null,
  };
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
    const H = helpfulRows.filter((r) => Date.parse(r.created_at) >= from.getTime());
    const helpful = H.length ? H.filter((r) => r.helpful).length / H.length : null;
    if (L.length === 0) return { errorRate: null, zeroRate: null, p50: null, helpful, helpfulN: H.length || null };
    return {
      errorRate: L.filter((r) => r.has_error).length / L.length,
      zeroRate: L.filter((r) => !r.has_error && r.result_count === 0).length / L.length,
      p50: p50(L.map((r) => r.latency_ms).filter((v): v is number => typeof v === "number")),
      helpful,
      helpfulN: H.length || null,
    };
  };
  const daily = Array.from({ length: 7 }, (_, i) => {
    const from = new Date(todayStart.getTime() - i * 86_400_000);
    return { date: kstDate(from), ...funnel(from, new Date(from.getTime() + 86_400_000)) };
  });

  return {
    todayKst,
    overview: {
      from: kstDate(completeStart), through: kstDate(new Date(todayStart.getTime() - 1)), previousFrom: kstDate(new Date(completeStart.getTime() - 7 * 86_400_000)),
      members: summarizeMembers(allUsers, saved.data, reviewed.data, completeStart.getTime(), todayStart.getTime(), excludedEmails),
      searches: summarizeSearches(logRows, completeStart.getTime(), todayStart.getTime()), pulse, issues,
      membersAvailable: !usersRes.error && !saved.error && !reviewed.error && !usersRes.truncated && !saved.truncated && !reviewed.truncated,
      searchesAvailable: !logs.error && !logs.truncated,
    },
    today: funnel(todayStart),
    week: funnel(weekStart),
    daily,
    health: { today: health(todayStart), week: health(weekStart) },
    zeroQueries: logRows.filter((r) => Date.parse(r.created_at) >= weekStart.getTime() && !r.has_error && r.result_count === 0).slice(0, 50).map((r) => toRow(r)),
    problemQueries: ((fb) => logRows.filter((r) => r.has_error && Date.parse(r.created_at) < todayStart.getTime()).slice(0, 30).map((r) => toRow(r, fb)))(fallbackKeys(logRows)),
    visits,
    conversions,
    feedback: ((fb.data ?? []) as { id: number; created_at: string; kind: FeedbackRow["kind"]; message: string; email: string | null; page: string | null; handled_at: string | null }[])
      .map((r) => ({ id: r.id, at: r.created_at, kind: r.kind, message: r.message, email: r.email, page: r.page, handled: !!r.handled_at })),
    interest,
    users: users
      .slice()
      .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      .map((u) => ({
        id: u.id, email: maskEmail(u.email), createdAt: u.created_at, lastSignInAt: u.last_sign_in_at ?? null,
        confirmed: !!u.email_confirmed_at,
        saved: savedRows.filter((r) => r.user_id === u.id).length,
        reviewed: reviewedRows.filter((r) => r.user_id === u.id).length,
      })),
    searches: logRows.filter((r) => Date.parse(r.created_at) >= weekStart.getTime()).slice(0, 200).map((r) => toRow(r)),
    savedRows: savedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bizrnoNorm: r.bizrno_norm, name: nameOf.get(r.bizrno_norm) ?? r.bizrno_norm })),
    reviewedRows: reviewedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bidNtceNo: r.bid_ntce_no, title: titleOf.get(r.bid_ntce_no) ?? r.bid_ntce_no })),
  };
}
