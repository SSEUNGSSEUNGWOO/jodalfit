// frontend/src/lib/entry.ts
// 입구 화면(04)의 판에 들어가는 수치·목록. 서버에서만 읽는다(service_role).
// 시안 docs/design/scripts/gen_entry_v2.py::fetch 와 같은 정의 — 숫자가 시안과 화면에서 달라지면 안 된다.
import "server-only";
import { unstable_cache } from "next/cache";
import { getServerSupabase } from "./supabase-server";
import { kstDate } from "./format";

export type EntryNotice = { nm: string; instt: string; clse: string | null; amt: number | null };
export type EntryData = {
  active: number; // 지금 입찰 가능 — 0057 funnel_counts 와 같은 정의(마감 90일·벡터·자격등록 안 지남)
  specOpen: number; // 의견 접수 중인 사전규격
  companies: number; // 벡터가 있는 회사
  fresh: EntryNotice[];
  freshToday: boolean; // 오늘 치가 충분한가 — 라벨이 바뀐다
  todayCount: number;
};

const ROWS = 5;
// 오늘 등록 건수가 이보다 적으면 "최근 등록"으로 바꿔 단다. 수집이 한 번 밀리면 한 자리로 떨어진다
// (2026-10-23 실측 9건 — ingest_bid_notices 타임아웃). 숫자를 꾸미지 않으면서 화면이 안 비게.
const TODAY_MIN = 20;

const ymd = kstDate;

// 입구는 모든 사람이 거치는 화면이고 nav 가 로그인 상태를 읽어 페이지 자체는 정적이 될 수 없다.
// 그래서 **데이터만** 캐시한다 — 요청마다 DB 를 다섯 번 치면 서버 응답이 1.7~1.9초가 된다
// (2026-10-23 Lighthouse, 운영 빌드). 수치는 분 단위로 바뀌는 값이 아니다.
export const getEntryData = unstable_cache(getEntryDataUncached, ["entry-data-v1"], {
  revalidate: 300,
  tags: ["entry-data"],
});

async function getEntryDataUncached(): Promise<EntryData> {
  const sb = getServerSupabase();
  const today = new Date();
  const horizon = new Date(today.getTime() + 90 * 86400_000);
  const nowIso = today.toISOString();
  const qlfctOk = `bid_qlfct_rgst_dt.is.null,bid_qlfct_rgst_dt.gt.${nowIso}`;
  // head: true — 행을 받지 않고 개수만 센다(8천 행을 끌어오지 않는다).
  const head = { count: "exact" as const, head: true };

  const [activeR, specR, coR, todayR] = await Promise.all([
    sb.from("bid_notices").select("*", head)
      .gte("bid_clse_date", ymd(today)).lte("bid_clse_date", ymd(horizon))
      .not("embedding_k", "is", null).or(qlfctOk),
    sb.from("pre_specs").select("*", head).gt("opnin_rgst_clse_dt", nowIso),
    sb.from("companies").select("*", head).not("embedding_k", "is", null).is("optout_at", null),
    sb.from("bid_notices").select("*", head).eq("bid_ntce_date", ymd(today)),
  ]);

  const todayCount = todayR.count ?? 0;
  const freshToday = todayCount >= TODAY_MIN;
  const since = new Date(today.getTime() - (freshToday ? 0 : 3) * 86400_000);

  // 갓 올라왔는데 이미 마감인 공고가 있다(재공고·정정) — 거르지 않으면 'D--1' 이 찍힌다.
  const { data } = await sb
    .from("bid_notices")
    .select("bid_ntce_no,bid_ntce_nm,dmnd_instt_nm,ntce_instt_nm,bid_ntce_date,bid_clse_date,presmpt_prce,asign_bdgt_amt")
    .gte("bid_ntce_date", ymd(since))
    .gte("bid_clse_date", ymd(today))
    .not("embedding_k", "is", null)
    .not("bid_ntce_nm", "is", null)
    .or(qlfctOk)
    .order("bid_ntce_date", { ascending: false })
    .order("bid_ntce_no", { ascending: false })
    .limit(120);

  // 나라장터가 같은 사업을 차수·재공고로 여러 번 올린다 — 제목+기관이 같으면 한 줄로 본다.
  const seen = new Set<string>();
  const fresh: EntryNotice[] = [];
  for (const r of data ?? []) {
    const instt = (r.dmnd_instt_nm as string | null) || (r.ntce_instt_nm as string | null) || "";
    const key = `${r.bid_ntce_nm}|${instt}`;
    if (seen.has(key)) continue;
    seen.add(key);
    fresh.push({
      nm: r.bid_ntce_nm as string,
      instt,
      clse: (r.bid_clse_date as string | null) ?? null,
      amt: (r.presmpt_prce as number | null) ?? (r.asign_bdgt_amt as number | null) ?? null,
    });
    if (fresh.length >= ROWS) break;
  }

  return {
    active: activeR.count ?? 0,
    specOpen: specR.count ?? 0,
    companies: coR.count ?? 0,
    fresh,
    freshToday,
    todayCount,
  };
}
