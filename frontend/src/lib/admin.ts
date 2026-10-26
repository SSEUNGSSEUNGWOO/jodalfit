// frontend/src/lib/admin.ts
// /admin 이 읽는 운영 숫자 — 전부 읽기 전용, service_role 로 서버에서만. 쓰기(사용자 삭제·비공개 처리)는 두지 않는다 —
// 사용자가 2명일 때 그건 Supabase 대시보드가 더 안전하다(2026-10-26 결정).
// 실사용 지표 규칙(CLAUDE.md "로그 지표"): search_logs 는 source = 'user' 만, notice_events 는 internal 을 뺀다.
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
export type Funnel = { searches: number; visitors: number; identified: number; clicks: number; signups: number; saved: number; reviewed: number };

export type AdminData = {
  todayKst: string;
  today: Funnel;
  week: Funnel;
  users: UserRow[];
  searches: SearchRow[];   // 최근 7일, 최신순, 최대 200
  savedRows: SavedRow[];
  reviewedRows: ReviewedRow[];
};

type LogRow = { created_at: string; query: string | null; mode: string | null; matched_corp_nm: string | null; matched_bizrno: string | null; result_count: number | null; has_error: boolean | null; ip_hash: string | null; referer: string | null };
type EventRow = { created_at: string; event_type: string; source: string | null };
type SavedKey = { user_id: string; bizrno_norm: string; created_at: string };
type ReviewedKey = { user_id: string; bid_ntce_no: string; bid_ntce_ord: string; created_at: string };

function refererHost(r: string | null): string | null {
  if (!r) return null;
  try {
    const u = new URL(r);
    return u.host.replace(/^www\./, "") + (u.host.endsWith("jodalfit.co.kr") ? u.pathname.replace(/\/$/, "") || "/" : "");
  } catch {
    return r.slice(0, 40);
  }
}

export async function fetchAdminData(now: Date = new Date()): Promise<AdminData> {
  const sb = getServerSupabase();
  const todayKst = kstDate(now);
  const todayStart = new Date(`${todayKst}T00:00:00+09:00`);
  const weekStart = new Date(todayStart.getTime() - 6 * 86_400_000);
  const since = weekStart.toISOString();

  const [logs, events, usersRes, saved, reviewed] = await Promise.all([
    sb.from("search_logs")
      .select("created_at,query,mode,matched_corp_nm,matched_bizrno,result_count,has_error,ip_hash,referer")
      .gte("created_at", since).eq("source", "user").order("created_at", { ascending: false }).limit(1000),
    sb.from("notice_events").select("created_at,event_type,source")
      .gte("created_at", since).eq("event_type", "click").neq("source", "internal").limit(5000),
    sb.auth.admin.listUsers({ page: 1, perPage: 200 }),
    sb.from("saved_companies").select("user_id,bizrno_norm,created_at").order("created_at", { ascending: false }).limit(200),
    sb.from("reviewed_notices").select("user_id,bid_ntce_no,bid_ntce_ord,created_at").order("created_at", { ascending: false }).limit(200),
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

  const funnel = (from: Date): Funnel => {
    const t = from.getTime();
    const inRange = (s: string) => Date.parse(s) >= t;
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

  return {
    todayKst,
    today: funnel(todayStart),
    week: funnel(weekStart),
    users: users
      .slice()
      .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      .map((u) => ({
        id: u.id, email: maskEmail(u.email), createdAt: u.created_at, lastSignInAt: u.last_sign_in_at ?? null,
        confirmed: !!u.email_confirmed_at,
        saved: savedRows.filter((r) => r.user_id === u.id).length,
        reviewed: reviewedRows.filter((r) => r.user_id === u.id).length,
      })),
    searches: logRows.slice(0, 200).map((r) => ({
      at: r.created_at, mode: r.mode ?? "—", query: r.query ?? "", matched: r.matched_corp_nm, matchedBizrno: r.matched_bizrno,
      results: r.result_count, error: !!r.has_error, ip: (r.ip_hash ?? "").slice(0, 4), referer: refererHost(r.referer),
    })),
    savedRows: savedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bizrnoNorm: r.bizrno_norm, name: nameOf.get(r.bizrno_norm) ?? r.bizrno_norm })),
    reviewedRows: reviewedRows.slice(0, 50).map((r) => ({ at: r.created_at, user: emailOf.get(r.user_id) ?? "—", bidNtceNo: r.bid_ntce_no, title: titleOf.get(r.bid_ntce_no) ?? r.bid_ntce_no })),
  };
}
