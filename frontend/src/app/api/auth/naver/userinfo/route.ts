// frontend/src/app/api/auth/naver/userinfo/route.ts
// 네이버 로그인용 userinfo 중계(2026-10-28). Supabase 는 네이버를 기본 공급자로 안 두므로 Custom OAuth 로 붙이는데,
// Supabase(auth/provider/custom_oauth.go)는 userinfo 응답의 **최상위** email·sub 만 읽는다. 네이버는 {resultcode, message, response:{id,email,…}}
// 로 한 겹 싸서 주므로 이 라우트가 같은 Bearer 토큰으로 네이버 /v1/nid/me 를 부르고 OIDC 모양으로 펴서 돌려준다.
// Supabase 공급자 설정의 UserInfo URL = https://jodalfit.co.kr/api/auth/naver/userinfo. 비밀값 없음 — 토큰은 요청자가 들고 온다.
// email_verified: 네이버 ID 메일(@naver.com)은 계정 그 자체라 검증됨. 그 밖의 연락처 메일은 false — Supabase 가 같은 메일의 기존 계정과 묶지 않고
// 새 계정으로 만든다(models/linking.go: 미검증 메일은 항상 새 계정). 남의 메일을 연락처로 적어 계정을 가로채는 길을 막는다.
import { NextResponse } from "next/server";

const NAVER_ME = "https://openapi.naver.com/v1/nid/me";

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
    email_verified: email.endsWith("@naver.com"),
    name: u.name || u.nickname || undefined,
    picture: u.profile_image || undefined,
  }, { headers: { "Cache-Control": "no-store" } });
}
