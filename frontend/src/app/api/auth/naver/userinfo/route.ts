// frontend/src/app/api/auth/naver/userinfo/route.ts
// 네이버 로그인용 userinfo 중계(2026-10-28). Supabase 는 네이버를 기본 공급자로 안 두므로 Custom OAuth 로 붙이는데,
// Supabase(auth/provider/custom_oauth.go)는 userinfo 응답의 **최상위** email·sub 만 읽는다. 네이버는 {resultcode, message, response:{id,email,…}}
// 로 한 겹 싸서 주므로 이 라우트가 같은 Bearer 토큰으로 네이버 /v1/nid/me 를 부르고 OIDC 모양으로 펴서 돌려준다.
// Supabase 공급자 설정의 UserInfo URL = https://jodalfit.co.kr/api/auth/naver/userinfo. 비밀값 없음 — 토큰은 요청자가 들고 온다.
// email_verified: 네이버 ID 메일(@naver.com)은 계정 그 자체라 검증됨. 그 밖의 연락처 메일은 네이버가 검증하지 않으므로, 같은 메일의
// 기존 계정이 있으면 false — Supabase 가 그 계정과 묶지 않고 확인 메일을 보낸다(models/linking.go: 미검증 메일은 항상 새 계정).
// 남의 메일을 연락처로 적어 계정을 가로채는 길을 막는다. 기존 계정이 없거나 이 네이버 identity 자신의 계정뿐이면 true —
// 묶일 계정이 없으니 위험이 없고, 확인 메일을 기다리느라 로그인을 못 하는 일(2026-10-29~30 네이버 가입 5명 중 3명이 옛 사서함
// empal·kornet·paran 주소라 멈춤)을 없앤다. 2026-11-02.
import { NextResponse } from "next/server";

const NAVER_ME = "https://openapi.naver.com/v1/nid/me";

type AdminUser = { id: string; email?: string | null; identities?: { provider: string; id: string }[] | null };

/** 같은 메일의 기존 계정이 없거나 전부 이 네이버 identity(sub) 의 계정이면 true. 조회 실패는 false(기존처럼 확인 메일). */
async function emailVerified(email: string, naverId: string): Promise<boolean> {
  if (email.endsWith("@naver.com")) return true;
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return false;
  const headers = { apikey: key, Authorization: `Bearer ${key}` };
  try {
    // GoTrue admin 목록의 filter 는 email ILIKE %filter% — 정확히 같은 주소만 남긴다. 목록 응답엔 identities 가 비어 있어 건별로 다시 읽는다.
    const list = await fetch(`${url}/auth/v1/admin/users?${new URLSearchParams({ filter: email, per_page: "10" })}`, { headers, cache: "no-store" });
    if (!list.ok) return false;
    const users = (((await list.json()) as { users?: AdminUser[] }).users ?? []).filter((u) => (u.email ?? "").toLowerCase() === email);
    for (const u of users) {
      const one = await fetch(`${url}/auth/v1/admin/users/${u.id}`, { headers, cache: "no-store" });
      if (!one.ok) return false;
      const ids = ((await one.json()) as AdminUser).identities ?? [];
      if (!ids.some((i) => i.provider === "custom:naver" && i.id === naverId)) return false;
    }
    return true;
  } catch {
    return false;
  }
}

export async function GET(req: Request) {
  const auth = req.headers.get("authorization") ?? "";
  if (!/^Bearer .+/i.test(auth)) return NextResponse.json({ error: "no_token" }, { status: 401 });
  let r: Response;
  try {
    r = await fetch(NAVER_ME, { headers: { Authorization: auth }, cache: "no-store" });
  } catch {
    return NextResponse.json({ error: "upstream" }, { status: 502 });
  }
  const body = (await r.json().catch(() => null)) as { resultcode?: string; response?: Record<string, string> } | null;
  if (!r.ok || body?.resultcode !== "00" || !body.response?.id) return NextResponse.json({ error: "naver", status: r.status }, { status: 401 });
  const u = body.response;
  const email = (u.email ?? "").trim().toLowerCase();
  return NextResponse.json({
    sub: u.id,
    email: email || undefined,
    email_verified: email ? await emailVerified(email, u.id) : false,
    name: u.name || u.nickname || undefined,
    picture: u.profile_image || undefined,
  }, { headers: { "Cache-Control": "no-store" } });
}
