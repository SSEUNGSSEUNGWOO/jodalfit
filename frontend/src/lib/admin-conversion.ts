export type ConversionEvent = { session: string; event: string; at: string; loggedIn: boolean | null };
export type ConversionCounts = { results: number; opened: number; intent: number; saved: number; guestIntent: number; signup: number };
export type Conversions = { today: ConversionCounts; week: ConversionCounts; error: string | null; truncated: boolean };

/** 결과 조회 이후 행동만 센다. 열기와 직접 저장은 별도 경로이며 가입 화면은 비로그인 저장 시도 이후만 센다. */
export function countConversions(events: ConversionEvent[], from: number): ConversionCounts {
  const sessions = new Map<string, ConversionEvent[]>();
  for (const e of events) {
    if (!e.session || !Number.isFinite(Date.parse(e.at))) continue;
    const group = sessions.get(e.session) ?? [];
    group.push(e); sessions.set(e.session, group);
  }
  const counts: ConversionCounts = { results: 0, opened: 0, intent: 0, saved: 0, guestIntent: 0, signup: 0 };
  for (const group of sessions.values()) {
    group.sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
    let viewed = false, intent = false, guest = false, opened = false, saved = false, signup = false;
    for (const e of group) {
      if (e.event === "results_view" && Date.parse(e.at) >= from) viewed = true;
      if (!viewed) continue;
      if (e.event === "notice_click") opened = true;
      if (e.event === "notice_save_intent") { intent = true; if (e.loggedIn === false) guest = true; }
      if (e.event === "notice_save" && intent) saved = true;
      if (e.event === "signup_view" && guest) signup = true;
    }
    counts.results += Number(viewed); counts.opened += Number(opened);
    counts.intent += Number(intent); counts.saved += Number(saved);
    counts.guestIntent += Number(guest); counts.signup += Number(signup);
  }
  return counts;
}
