// frontend/src/app/api/consent/marketing/route.ts
// 로그인한 사용자의 알림 메일 수신 여부만 바꾼다 — /welcome 의 메일 체크(2026-11-09).
// 검토함 토글과 메일 하단 "그만 받기"는 HMAC 링크를 받는 /api/mail/weekly 를 쓴다(세션 없이도 동작해야 해서). 여기는 세션만 본다.
// 바꾸는 열은 0052 user_consents.marketing_opt_in 하나(lock 트리거가 허용하는 유일한 열). service_role 로 쓴다.
import { NextResponse } from "next/server";
import { getServerSupabase as getSessionSupabase } from "@/lib/supabase/server";
import { getServerSupabase as getPublicSupabase } from "@/lib/supabase-server";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { on?: unknown } | null;
  if (typeof body?.on !== "boolean") return NextResponse.json({ error: "bad" }, { status: 400 });

  const session = await getSessionSupabase({ strict: true });
  const { data: { user } } = await session.auth.getUser();
  if (!user) return NextResponse.json({ error: "auth" }, { status: 401 });

  const { error } = await getPublicSupabase().from("user_consents").update({ marketing_opt_in: body.on }).eq("user_id", user.id);
  if (error) return NextResponse.json({ error: "db" }, { status: 500 });
  return NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
}
