// frontend/src/app/api/consent/route.ts
// 소셜 가입의 동의 기록(2026-10-28) — /consent 한 판에서 받은 필수 둘(이용약관·개인정보)과 선택(알림 메일)을 user_consents 에 채운다.
// 가입 폼은 user_metadata 로 넘겨 0052 트리거가 쓰지만 OAuth 는 그 길이 없어 ''/'' 행으로 생긴다. 0064 가 빈 행만 한 번 채우게 허용한다.
// 사용자는 세션으로 확인하고, 쓰기는 service_role(terms_version 은 사용자 권한으로 update 불가 — 0052 grant).
import { NextResponse } from "next/server";
import { PRIVACY_VERSION } from "@/lib/privacy";
import { TERMS_VERSION } from "@/lib/terms";
import { getServerSupabase as getSessionSupabase } from "@/lib/supabase/server";
import { getServerSupabase as getPublicSupabase } from "@/lib/supabase-server";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { terms?: unknown; privacy?: unknown; marketing?: unknown } | null;
  if (body?.terms !== true || body?.privacy !== true) return NextResponse.json({ error: "required" }, { status: 400 });
  const marketing = body.marketing === true;

  const session = await getSessionSupabase({ strict: true });
  const { data: { user } } = await session.auth.getUser();
  if (!user) return NextResponse.json({ error: "auth" }, { status: 401 });

  const sb = getPublicSupabase();
  const { data: row } = await sb.from("user_consents").select("terms_version").eq("user_id", user.id).maybeSingle();
  const filled = { terms_version: TERMS_VERSION, privacy_version: PRIVACY_VERSION, marketing_opt_in: marketing, consented_at: new Date().toISOString() };
  const { error } = row
    ? (row.terms_version === "" ? await sb.from("user_consents").update(filled).eq("user_id", user.id).eq("terms_version", "") : { error: null }) // 이미 동의한 행은 그대로(불변)
    : await sb.from("user_consents").insert({ user_id: user.id, ...filled });
  if (error) return NextResponse.json({ error: "db" }, { status: 500 });
  return NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
}
