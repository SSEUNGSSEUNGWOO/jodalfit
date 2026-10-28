// frontend/src/app/api/saved/companies/route.ts
// 회사 이름(또는 사업자등록번호) 하나를 받아 현재 사용자의 saved_companies 에 넣는다 — /welcome·검토함 빈 상태의 저장 폼(2026-10-28).
// 자동완성(companies/suggest)은 사업자번호를 싣지 않으므로 이름을 받아 여기서 되찾는다: 정확히 같은 회사명(계약 많은 행) 또는 10자리 번호.
// 되찾기는 service_role, 넣기는 사용자 세션(RLS, user_id 는 auth.uid() 기본값) — StarCompany 와 같은 표·같은 규칙.
import { NextResponse } from "next/server";
import { getServerSupabase as getSessionSupabase } from "@/lib/supabase/server";
import { getServerSupabase as getPublicSupabase } from "@/lib/supabase-server";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { nm?: unknown } | null;
  const nm = typeof body?.nm === "string" ? body.nm.trim() : "";
  if (!nm || nm.length > 50) return NextResponse.json({ error: "bad" }, { status: 400 });

  const session = await getSessionSupabase({ strict: true });
  const { data: { user } } = await session.auth.getUser();
  if (!user) return NextResponse.json({ error: "auth" }, { status: 401 });

  const pub = getPublicSupabase();
  const digits = nm.replace(/-/g, "");
  let query = pub.from("companies").select("bizrno_norm,corp_nm").is("optout_at", null).not("embedding_k", "is", null);
  query = /^\d{10}$/.test(digits) ? query.eq("bizrno_norm", digits) : query.eq("corp_nm", nm);
  const { data } = await query.order("contract_count", { ascending: false, nullsFirst: false }).limit(1);
  const co = data?.[0] as { bizrno_norm: string; corp_nm: string } | undefined;
  if (!co) return NextResponse.json({ error: "notfound" }, { status: 404 });

  const { error } = await session.from("saved_companies").insert({ bizrno_norm: co.bizrno_norm });
  if (error && error.code !== "23505") return NextResponse.json({ error: "db" }, { status: 500 }); // 23505 = 이미 저장됨
  return NextResponse.json({ bizrnoNorm: co.bizrno_norm, name: co.corp_nm }, { headers: { "Cache-Control": "no-store" } });
}
