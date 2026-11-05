export type MemberInput = { id: string; email?: string; created_at: string; email_confirmed_at?: string | null };
export type SavedInput = { user_id: string };
export type MemberSummary = { total: number; confirmed: number; newMembers: number; previousNewMembers: number; companyUsers: number; companies: number; noticeUsers: number; notices: number; excluded: number };
export type SearchInput = { created_at: string; has_error: boolean | null; error_msg: string | null; query: string | null; mode: string | null };
export type SearchSummary = { total: number; problems: number; missingCompany: number; missingProfile: number; other: number };
export type Pulse = { visitors: number; previousVisitors: number; views: number; previousViews: number; returning: number; searchers: number; resultViewers: number; outboundUsers: number; outboundClicks: number; error: string | null };
export type AdminOverview = { from: string; through: string; previousFrom: string; members: MemberSummary; searches: SearchSummary; pulse: Pulse; issues: string[]; membersAvailable: boolean; searchesAvailable: boolean };

export function isExcludedMember(email: string | undefined, excludedEmails: string[]): boolean {
  const normalized = (email ?? "").trim().toLowerCase();
  return normalized.endsWith("@jodalfit.test") || excludedEmails.some((e) => e.trim().toLowerCase() === normalized);
}

export function summarizeMembers(users: MemberInput[], companies: SavedInput[], notices: SavedInput[], from: number, until: number, excludedEmails: string[]): MemberSummary {
  const included = users.filter((u) => !isExcludedMember(u.email, excludedEmails));
  const ids = new Set(included.map((u) => u.id));
  const saved = companies.filter((s) => ids.has(s.user_id));
  const reviewed = notices.filter((s) => ids.has(s.user_id));
  const signups = (start: number, end: number) => included.filter((u) => { const at = Date.parse(u.created_at); return at >= start && at < end; }).length;
  return { total: included.length, confirmed: included.filter((u) => !!u.email_confirmed_at).length,
    newMembers: signups(from, until), previousNewMembers: signups(from - (until - from), from),
    companyUsers: new Set(saved.map((s) => s.user_id)).size, companies: saved.length,
    noticeUsers: new Set(reviewed.map((s) => s.user_id)).size, notices: reviewed.length, excluded: users.length - included.length };
}

export function summarizeSearches(rows: SearchInput[], from: number, until: number): SearchSummary {
  const selected = rows.filter((r) => Date.parse(r.created_at) >= from && Date.parse(r.created_at) < until);
  const failed = selected.filter((r) => r.has_error);
  const missingCompany = failed.filter((r) => (r.error_msg ?? "").includes("회사를 찾을 수")).length;
  const missingProfile = failed.filter((r) => !(r.error_msg ?? "").includes("회사를 찾을 수") && (r.error_msg ?? "").includes("등록업종")).length;
  return { total: selected.length, problems: failed.length, missingCompany, missingProfile, other: failed.length - missingCompany - missingProfile };
}

/** 서버의 기본 행 상한에 잘리지 않도록 페이지를 읽고, 일부만 읽은 경우를 표시한다. */
export async function readAdminRows<T>(read: (from: number, to: number) => PromiseLike<{ data: T[] | null; error: { message: string } | null }>, pageSize = 1000, limit = 10000): Promise<{ data: T[]; error: string | null; truncated: boolean }> {
  const data: T[] = [];
  try {
    while (data.length < limit) {
      const size = Math.min(pageSize, limit - data.length);
      const result = await read(data.length, data.length + size - 1);
      if (result.error) return { data: [], error: result.error.message, truncated: false };
      const rows = result.data ?? [];
      data.push(...rows);
      if (rows.length < size) return { data, error: null, truncated: false };
    }
    const extra = await read(limit, limit);
    if (extra.error) return { data: [], error: extra.error.message, truncated: false };
    return { data, error: null, truncated: !!extra.data?.length };
  } catch { return { data: [], error: "조회 연결 실패", truncated: false }; }
}
