// frontend/scripts/auth_smoke.mjs
// 실행: cd frontend && node --env-file=.env.local scripts/auth_smoke.mjs   (BASE 는 AUTH_URL, 기본 http://localhost:3000)
import { createClient } from "@supabase/supabase-js";

const BASE = process.env.AUTH_URL ?? "http://localhost:3000";
const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 필요(.env.local)");
if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) throw new Error("NEXT_PUBLIC_SUPABASE_ANON_KEY 필요(.env.local)");
const admin = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
const email = `smoke+${Date.now()}@jodalfit.co.kr`, password = "smoke-pass-12345";
const meta = { terms_version: "2026-10-19", privacy_version: "2026-10-19", marketing_opt_in: true, consented_at: new Date().toISOString() };

async function hit(path) {
  const r = await fetch(BASE + path, { redirect: "manual" });
  return { status: r.status, location: r.headers.get("location"), cookie: r.headers.get("set-cookie") ?? "" };
}

let userId;
try {
  // 1) 가입 확인 링크 — 미확인 사용자 생성 → signup 링크 → /auth/confirm → next 로 302 + sb- 쿠키
  const { data: created, error: e1 } = await admin.auth.admin.createUser({ email, password, email_confirm: false, user_metadata: meta });
  if (e1) throw e1; userId = created.user.id;
  const { data: l1, error: e2 } = await admin.auth.admin.generateLink({ type: "signup", email, password, options: { redirectTo: `${BASE}/auth/confirm?next=%2Fdev%2Ffoundation` } });
  if (e2) throw e2;
  const r1 = await hit(`/auth/confirm?next=%2Fdev%2Ffoundation&token_hash=${l1.properties.hashed_token}&type=signup`);
  if (!(r1.status >= 300 && r1.status < 400)) throw new Error(`confirm(signup) status ${r1.status}`);
  if (!r1.location?.endsWith("/dev/foundation")) throw new Error(`confirm(signup) location ${r1.location}`);
  if (!/sb-.*-auth-token/.test(r1.cookie)) throw new Error("confirm(signup) 세션 쿠키 없음");
  // 2) 같은 링크 재사용 → /login?error=link
  const r1b = await hit(`/auth/confirm?next=%2Fdev%2Ffoundation&token_hash=${l1.properties.hashed_token}&type=signup`);
  if (!r1b.location?.includes("/login?error=link")) throw new Error(`재사용 링크가 막히지 않음: ${r1b.location}`);
  // 3) 동의 기록 — 트리거
  const { data: consent } = await admin.from("user_consents").select("*").eq("user_id", userId).maybeSingle();
  if (!consent || consent.terms_version !== meta.terms_version || consent.marketing_opt_in !== true) throw new Error(`user_consents 불일치: ${JSON.stringify(consent)}`);
  // 3b) authenticated RLS — 본인 동의 읽기는 되고, 잠긴 컬럼 수정은 막힌다
  const anon = createClient(url, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, { auth: { persistSession: false } });
  const { error: eIn } = await anon.auth.signInWithPassword({ email, password });
  if (eIn) throw eIn;
  const { data: mine, error: eSel } = await anon.from("user_consents").select("marketing_opt_in").eq("user_id", userId).maybeSingle();
  if (eSel || !mine) throw new Error(`RLS 자기 동의 읽기 실패: ${eSel?.message}`);
  const { error: eUp } = await anon.from("user_consents").update({ terms_version: "hack" }).eq("user_id", userId);
  if (!eUp) throw new Error("terms_version 변경이 막히지 않음");
  // 4) 재설정 링크 → /reset/new 로 302 + 쿠키
  const { data: l2, error: e3 } = await admin.auth.admin.generateLink({ type: "recovery", email, options: { redirectTo: `${BASE}/auth/confirm?next=%2Freset%2Fnew` } });
  if (e3) throw e3;
  const r2 = await hit(`/auth/confirm?next=%2Freset%2Fnew&token_hash=${l2.properties.hashed_token}&type=recovery`);
  if (!r2.location?.endsWith("/reset/new") || !/sb-.*-auth-token/.test(r2.cookie)) throw new Error(`confirm(recovery) ${r2.status} ${r2.location}`);
  // 5) 가짜 토큰은 거부 (safeNext 자체는 lib/safe-next.test.ts 가 검증)
  const r3 = await hit(`/auth/confirm?next=https%3A%2F%2Fevil.example&token_hash=bogus&type=signup`);
  if (!r3.location?.includes("/login?error=link")) throw new Error(`bogus token: ${r3.location}`);
  // 6) 로그아웃 라우트
  const r4 = await hit("/logout");
  if (!(r4.status >= 300 && r4.status < 400) || !r4.location?.includes("/?logout=1")) throw new Error(`logout ${r4.status} ${r4.location}`);
  console.log("ok auth smoke: signup confirm → next + cookie · reuse blocked · consents row · recovery → /reset/new · bogus next blocked · logout · RLS own read · immutable");
} finally {
  if (userId) await admin.auth.admin.deleteUser(userId);
}
