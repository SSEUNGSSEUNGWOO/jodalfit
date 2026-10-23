// frontend/src/app/api/companies/suggest/route.ts
// 입구 검색창 자동완성 — 회사명으로 거른 후보 목록. 공개 데이터, service_role 로 읽는다.
//
// 돌려주는 건 이름·지역·등록업종 수뿐이다. **사업자번호는 싣지 않는다**(README §12 마스킹) —
// 고르는 데 필요 없고, 목록에서 긁어가는 통로가 되면 안 된다. 선택은 회사명으로 넘긴다.
// 비공개 요청(optout_at) 회사는 애초에 제외한다.
import { NextResponse } from "next/server";
import { getServerSupabase } from "@/lib/supabase-server";

export type CompanySuggestion = { nm: string; rgn: string; industries: number };

const LIMIT = 6;

export async function GET(req: Request) {
  const q = (new URL(req.url).searchParams.get("q") ?? "").trim();
  // 두 글자 미만은 후보가 수천 개라 의미가 없다 — 프로토타입과 같은 문턱.
  if (q.length < 2) return NextResponse.json<CompanySuggestion[]>([]);

  const sb = getServerSupabase();
  // ilike 는 pg_trgm 인덱스를 탄다(companies_corp_nm_trgm). 벡터가 있는 회사만 — 추천이 되는 회사라야 고를 값이 있다.
  const { data, error } = await sb
    .from("companies")
    .select("bizrno,corp_nm,rgn_nm")
    .ilike("corp_nm", `%${q}%`)
    .is("optout_at", null)
    .not("embedding_k", "is", null)
    .order("contract_count", { ascending: false, nullsFirst: false })
    .limit(LIMIT * 3); // 같은 이름이 하이픈 유무로 두 행인 경우가 있다 — 넉넉히 받아 이름으로 접는다
  if (error || !data?.length) return NextResponse.json<CompanySuggestion[]>([]);

  // 같은 회사명+지역은 한 줄로. 먼저 온 행(계약 많은 쪽)을 남긴다.
  const seen = new Set<string>();
  const picked = data.filter((r) => {
    const k = `${r.corp_nm}|${r.rgn_nm ?? ""}`;
    if (!r.corp_nm || seen.has(k)) return false;
    seen.add(k);
    return true;
  }).slice(0, LIMIT);

  // 등록업종 수 — company_industries.bizrno 는 하이픈 포함 원본 형식이라 companies.bizrno 로 센다.
  const counts = new Map<string, number>();
  const keys = picked.map((r) => r.bizrno).filter(Boolean) as string[];
  if (keys.length) {
    const { data: inds } = await sb.from("company_industries").select("bizrno").in("bizrno", keys);
    for (const row of inds ?? []) counts.set(row.bizrno, (counts.get(row.bizrno) ?? 0) + 1);
  }

  const body: CompanySuggestion[] = picked.map((r) => ({
    nm: r.corp_nm as string,
    rgn: (r.rgn_nm as string | null) ?? "",
    industries: counts.get(r.bizrno as string) ?? 0,
  }));
  return NextResponse.json(body, {
    headers: { "Cache-Control": "public, s-maxage=300, stale-while-revalidate=3600" },
  });
}
