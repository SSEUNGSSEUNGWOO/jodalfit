# 리뉴얼 02 — auth: 로그인 · 회원가입 · 재설정 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 먼저 `2026-10-19-renewal-00-master.md` §3.2·§3.3·§3.7 과 01 계획의 부품(`Nav` `Btn` `Panel` `PageHead` `SiteFooter`)을 읽는다. 시안: `docs/design/prototypes/login-final.html`, 원천 `docs/design/scripts/gen_login.py`.

**Goal:** Supabase Auth(이메일 + 비밀번호, 확인 메일 1회, 재설정 메일)를 `@supabase/ssr` 쿠키 세션으로 붙이고, 시안의 장면(로그인 → 회원가입 → 확인 메일 보냄 → 메일 링크 → 로그인됨 / 재설정 → 새 비밀번호 / 로그아웃)을 `(renewal)` 레이아웃 위에 만든다. 동의(약관·개인정보 필수, 알림 선택)는 가입 시 메타데이터로 받아 트리거가 `user_consents`(0052)에 남긴다. `/terms` 와 개인정보처리방침 개정을 포함한다.

**Architecture:** 브라우저에서는 `createBrowserClient`(anon 키)로 `signInWithPassword`/`signUp`/`resetPasswordForEmail`/`updateUser` 를 직접 호출하고, 서버(레이아웃·라우트 핸들러)는 `createServerClient` + `await cookies()` 로 세션을 읽는다. `src/proxy.ts`(Next 16; `middleware` 아님)가 매 요청 토큰을 갱신한다. 메일 링크는 `token_hash` 방식(`/auth/confirm?token_hash&type&next`)으로 라우트 핸들러가 `verifyOtp` 해 쿠키를 세팅하고 `safeNext` 로 돌려보낸다. 새 페이지는 `src/app/(renewal)/` 라우트 그룹의 공용 레이아웃(바닥 + `Nav` + `SiteFooter`) 아래 둔다. 서버 액션은 쓰지 않는다(폼이 셋뿐, 클라이언트 직접 호출이 가장 짧다).

**Tech Stack:** Next.js 16.2(App Router, `proxy.ts`, async `cookies()`) · React 19 · `@supabase/ssr` 0.10 + `@supabase/supabase-js` 2 · Supabase Auth(Confirm email ON, 비밀번호 8자, OTP 60분) · Resend SMTP(Supabase Custom SMTP) · Postgres(0052) · Playwright(backend venv) + Node 스모크(`admin.generateLink` 로 메일 없이 확인 링크 검증).

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `frontend/.env.local`, `.env.local.example` | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` 추가(브라우저 인증 클라이언트). Vercel 에도 같은 둘 |
| `frontend/src/lib/safe-next.ts` + `safe-next.test.ts` | `safeNext(raw, fallback)` — 상대 경로만 허용 |
| `frontend/src/lib/terms.ts` | `TERMS_VERSION`(시행일). `lib/privacy.ts` 의 `PRIVACY_VERSION` 과 한 쌍 |
| `frontend/src/lib/supabase/browser.ts` | `getBrowserSupabase()` — 클라이언트 컴포넌트용 |
| `frontend/src/lib/supabase/server.ts` | `getServerSupabase()` — 서버 컴포넌트·라우트 핸들러용(쿠키 읽기/쓰기) |
| `frontend/src/proxy.ts` | 세션 갱신. 매처는 정적 자산 제외 |
| `frontend/src/lib/auth.ts` | `getSessionUser()` · `getNavUser()`(03 전까지 `savedCompanies: []`, `reviewedCount: 0`) |
| `frontend/src/app/(renewal)/layout.tsx` | `.rn bg-paper` 바닥 + `Nav user` + `SiteFooter`. 02 의 모든 페이지와 `/dev/foundation` 이 이 아래로 |
| `frontend/src/app/dev/foundation/page.tsx` → `frontend/src/app/(renewal)/dev/foundation/page.tsx` | 이동 + 자체 Nav/바닥 제거(중첩 `.rn` 해소) |
| `frontend/src/components/Nav.tsx` | 로그인 링크에 쿼리 포함(`useSearchParams`, Suspense), `role=menu` 제거, Escape 시 트리거로 포커스 복귀 |
| `frontend/scripts/check_foundation.py` | 메뉴 검사 `menuitem == 5` → `[data-menu] a` == 5, URL 기본값 유지 |
| `frontend/src/components/Field.tsx` | `TextField`·`PasswordField`(표시/숨김) — 46px, 주황 포커스 링 |
| `frontend/src/components/Consent.tsx` | 동의 세 줄(약관 필수 · 개인정보 필수 · 알림 선택) |
| `frontend/src/components/Narrow.tsx` | 좁은 판(520px): 제목 28 + `Panel` |
| `frontend/src/app/(renewal)/login/page.tsx` + `LoginForm.tsx` | 장면 1 |
| `frontend/src/app/(renewal)/signup/page.tsx` + `SignupForm.tsx` | 장면 2 |
| `frontend/src/app/(renewal)/signup/sent/page.tsx` + `ResendButton.tsx` | 장면 3(60초 뒤 다시 보내기) |
| `frontend/src/app/auth/confirm/route.ts` | 메일 링크 → `verifyOtp` → 쿠키 → `safeNext` 로 이동. 실패 시 `/login?error=link` |
| `frontend/src/app/(renewal)/reset/page.tsx` + `ResetForm.tsx` | 장면 6 |
| `frontend/src/app/(renewal)/reset/new/page.tsx` + `NewPasswordForm.tsx` | 장면 6c(세션 필요 — recovery 링크로 들어온 상태) |
| `frontend/src/app/logout/route.ts` | `signOut` 후 `/` 로 |
| `frontend/src/app/(renewal)/terms/page.tsx` | 이용약관(초안 — 승우님 검토 후 시행일 확정) |
| `frontend/src/app/privacy/page.tsx`, `frontend/src/lib/privacy.ts` | 계정(이메일·비밀번호 해시·동의 기록) 항목 추가, `PRIVACY_VERSION` 올림 |
| `supabase/migrations/0052_user_consents.sql` | 테이블 + RLS + `auth.users` 트리거 |
| `frontend/scripts/auth_smoke.mjs` | 메일 없이 가입 확인·재설정 링크 왕복 검증(service_role `admin.generateLink`) |
| `frontend/scripts/check_auth.py` | 페이지 정적 동작·문구·390 검증 |
| `docs/design/README.md` | 구현 02 기록 |

수동 작업(코드 밖, Task 1·2 에 체크리스트): Supabase Auth 설정 · Custom SMTP(Resend) · 메일 템플릿 · Redirect URL · Resend 도메인 DNS.

---

### Task 1: Supabase Auth · Resend 설정 (수동 체크리스트)

**Files:** 없음. 대시보드 작업. 완료 전에는 Task 9(스모크)가 통과할 수 없다.

- [ ] **Step 1: Supabase → Authentication → Providers → Email**
  - Enable Email provider: ON · Confirm email: **ON** · Secure email change: ON · Secure password change: **ON**(오래된 세션이 기존 비밀번호 없이 변경하는 것을 막는다 — recovery 링크 로그인은 최근 인증으로 인정) · Minimum password length: **8** · Password requirements: No required characters(길이만)
- [ ] **Step 2: Authentication → Settings(URL Configuration)**
  - Site URL: `https://jodalfit.co.kr`
  - Redirect URLs 추가: `http://localhost:3000/**`, `http://localhost:3001/**`, `https://*.vercel.app/**`, `https://jodalfit.co.kr/**`
  - Email OTP expiry: **3600**(60분). (Auth → Settings → "Email OTP Expiration")
- [ ] **Step 3: Resend** — 도메인 `jodalfit.co.kr` 추가 → 안내된 SPF·DKIM(TXT/CNAME) 레코드를 DNS 에 등록 → Verified 될 때까지 대기 → API Key 발급(이름 `supabase-smtp`, Sending access)
- [ ] **Step 4: Supabase → Project Settings → Authentication → SMTP Settings** — Enable Custom SMTP
  - Sender email `noreply@jodalfit.co.kr` · Sender name `조달핏` · Host `smtp.resend.com` · Port `465` · Username `resend` · Password = Resend API Key
- [ ] **Step 5: Authentication → Email Templates** — 두 템플릿을 아래로 교체(`{{ .RedirectTo }}` 는 앱이 보낸 `emailRedirectTo`/`redirectTo`, 거기에 이미 `?next=` 가 들어 있으므로 `&` 로 잇는다)

  **Confirm signup** — Subject `조달핏 이메일 확인 (60분 유효)`
  ```html
  <div style="font-family:Pretendard,Apple SD Gothic Neo,sans-serif;max-width:560px;margin:0 auto;padding:28px 24px;color:#141414;font-size:14.5px;line-height:1.7">
    <p style="font-weight:800;font-size:15px;margin:0 0 20px">조달핏</p>
    <h2 style="font-size:20px;font-weight:650;margin:0 0 10px">이메일 확인</h2>
    <p style="margin:0 0 10px">아래 버튼을 누르면 가입이 완료됩니다.</p>
    <p style="margin:14px 0 18px"><a href="{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=signup" style="display:inline-block;background:#141414;color:#fff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:8px">이메일 확인</a></p>
    <p style="margin:0 0 10px">유효 60분 · 1회. 버튼이 동작하지 않으면 아래 주소를 브라우저에 입력합니다.</p>
    <p style="font-size:12.5px;color:#6b6b67;word-break:break-all;margin:0">{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=signup</p>
    <p style="margin:22px 0 0;padding-top:14px;border-top:1px solid #ececea;font-size:12px;color:#737370">{{ .Email }} 의 가입 요청으로 발송된 메일입니다. 요청한 적이 없으면 무시하십시오.<br>조달핏 · jodalfit.co.kr</p>
  </div>
  ```
  **Reset password** — Subject `조달핏 비밀번호 재설정 (60분 유효)`
  ```html
  <div style="font-family:Pretendard,Apple SD Gothic Neo,sans-serif;max-width:560px;margin:0 auto;padding:28px 24px;color:#141414;font-size:14.5px;line-height:1.7">
    <p style="font-weight:800;font-size:15px;margin:0 0 20px">조달핏</p>
    <h2 style="font-size:20px;font-weight:650;margin:0 0 10px">비밀번호 재설정</h2>
    <p style="margin:0 0 10px">아래 버튼을 누르면 새 비밀번호를 정하는 화면이 열립니다.</p>
    <p style="margin:14px 0 18px"><a href="{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=recovery" style="display:inline-block;background:#141414;color:#fff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:8px">비밀번호 재설정</a></p>
    <p style="margin:0 0 10px">유효 60분 · 1회. 버튼이 동작하지 않으면 아래 주소를 브라우저에 입력합니다.</p>
    <p style="font-size:12.5px;color:#6b6b67;word-break:break-all;margin:0">{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=recovery</p>
    <p style="margin:22px 0 0;padding-top:14px;border-top:1px solid #ececea;font-size:12px;color:#737370">{{ .Email }} 의 비밀번호 재설정 요청으로 발송된 메일입니다. 요청한 적이 없으면 무시하십시오.<br>조달핏 · jodalfit.co.kr</p>
  </div>
  ```
- [ ] **Step 6: 키 복사** — Project Settings → API 의 Project URL · anon public key 를 Task 2 에 쓴다. 완료 확인: Authentication → Users 에서 아무 메일로 "Invite"를 보내 Resend 대시보드 Emails 에 발송 기록이 뜨면 SMTP 연결 끝(초대 사용자는 삭제).

---

### Task 2: 환경변수

**Files:**
- Modify: `frontend/.env.local`, `frontend/.env.local.example`

- [ ] **Step 1: `.env.local` 에 두 줄 추가**(값은 Task 1 Step 6)
```
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon public key>
```
- [ ] **Step 2: `.env.local.example`** — 이미 두 키가 1·2행에 있다. 주석만 보강: `# 브라우저 인증 클라이언트(@supabase/ssr) 용. anon 키는 공개 가능, service_role 은 절대 아님.`
- [ ] **Step 3: Vercel** — Project → Settings → Environment Variables 에 같은 두 키(Production·Preview). 확인: `npx vercel env ls` 에 둘 다.
- [ ] **Step 4: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/.env.local.example && git commit -m "chore(renewal): 브라우저 Supabase 키 환경변수 설명"
```

---

### Task 3: `safeNext` + `TERMS_VERSION`

**Files:**
- Create: `frontend/src/lib/safe-next.ts`, `frontend/src/lib/safe-next.test.ts`, `frontend/src/lib/terms.ts`

- [x] **Step 1: 테스트**
```ts
// frontend/src/lib/safe-next.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { safeNext } from "./safe-next.ts";

test("safeNext — 상대 경로만 통과", () => {
  assert.equal(safeNext("/saved"), "/saved");
  assert.equal(safeNext("/recommendations?company=%ED%95%9C%EC%A2%85&mode=company"), "/recommendations?company=%ED%95%9C%EC%A2%85&mode=company");
  assert.equal(safeNext("/companies/1248177731#top"), "/companies/1248177731#top");
});

test("safeNext — 밖으로 나가는 것은 전부 기본값", () => {
  assert.equal(safeNext("https://evil.example/x"), "/recommendations");
  assert.equal(safeNext("//evil.example"), "/recommendations");
  assert.equal(safeNext("/\\evil.example"), "/recommendations");
  assert.equal(safeNext("javascript:alert(1)"), "/recommendations");
  assert.equal(safeNext("saved"), "/recommendations");
  assert.equal(safeNext(""), "/recommendations");
  assert.equal(safeNext(null), "/recommendations");
  assert.equal(safeNext(undefined, "/"), "/");
});

test("safeNext — 로그인·가입 페이지로 되돌아가지 않는다", () => {
  assert.equal(safeNext("/login?next=/saved"), "/recommendations");
  assert.equal(safeNext("/signup"), "/recommendations");
  assert.equal(safeNext("/auth/confirm?x=1"), "/recommendations");
});
```
- [x] **Step 2: 실패 확인** — `cd C:/Dev/personal/jodalfit/frontend && node --test src/lib/safe-next.test.ts` → `Cannot find module`
- [x] **Step 3: 구현**
```ts
// frontend/src/lib/safe-next.ts
/** 로그인·가입·확인 뒤 돌아갈 곳. 상대 경로(`/` 하나로 시작)만 허용 — 오픈 리다이렉트 방지(renewal-00 §3.2). */
const AUTH_PATHS = /^\/(login|signup|reset|auth\/|logout)/;

export function safeNext(raw: string | null | undefined, fallback = "/recommendations"): string {
  if (!raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return fallback;
  if (raw.includes("://") || /[\u0000-\u001f]/.test(raw)) return fallback;
  if (AUTH_PATHS.test(raw)) return fallback;
  return raw;
}
```
```ts
// frontend/src/lib/terms.ts
/** 이용약관 시행일. 내용이 바뀌면 올린다. user_consents.terms_version 에 남는다. lib/privacy.ts 의 PRIVACY_VERSION 과 같은 역할. */
export const TERMS_VERSION = "2026-10-19";
```
- [x] **Step 4: 통과** — `node --test src/lib/safe-next.test.ts` → `# pass 3`
- [x] **Step 5: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/lib/safe-next.ts frontend/src/lib/safe-next.test.ts frontend/src/lib/terms.ts && git commit -m "feat(renewal): safeNext(상대 경로만) + TERMS_VERSION"
```

---

### Task 4: Supabase 클라이언트 · proxy · 세션 헬퍼

**Files:**
- Create: `frontend/src/lib/supabase/browser.ts`, `frontend/src/lib/supabase/server.ts`, `frontend/src/proxy.ts`, `frontend/src/lib/auth.ts`

- [x] **Step 1: browser**
```ts
// frontend/src/lib/supabase/browser.ts
"use client";

import { createBrowserClient } from "@supabase/ssr";

let client: ReturnType<typeof createBrowserClient> | null = null;

/** 클라이언트 컴포넌트 전용(anon 키). 쿠키에 세션을 쓰므로 서버(`lib/supabase/server.ts`)와 같은 세션을 본다. */
export function getBrowserSupabase() {
  if (!client) {
    client = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
  }
  return client;
}
```
- [x] **Step 2: server**
```ts
// frontend/src/lib/supabase/server.ts
import "server-only";
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

/**
 * 서버 컴포넌트·라우트 핸들러용(anon 키 + 요청 쿠키). 사용자 세션으로 RLS 테이블을 읽고 쓴다.
 * 공개 데이터 SSR 은 기존 `lib/supabase-server.ts`(service_role) 그대로 — 둘을 섞지 않는다.
 * 서버 컴포넌트에서는 setAll 이 실패할 수 있다(읽기 전용 렌더) — proxy.ts 가 갱신을 맡으므로 삼킨다.
 * 라우트 핸들러에서는 { strict: true } — 쿠키 쓰기 실패를 숨기지 않는다. 라우트 핸들러의 리다이렉트 응답에는 Cache-Control: no-store 를 직접 붙인다(Task 7).
 */
export async function getServerSupabase({ strict = false }: { strict?: boolean } = {}) {
  const store = await cookies();
  return createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookies: {
      getAll() { return store.getAll(); },
      setAll(cookiesToSet) {
        try { cookiesToSet.forEach(({ name, value, options }) => store.set(name, value, options)); }
        catch (e) { if (strict) throw e; /* 서버 컴포넌트 렌더 중 — proxy 가 갱신 */ }
      },
    },
  });
}
```
- [x] **Step 3: proxy**
```ts
// frontend/src/proxy.ts
import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

let warned = false;

/** 매 요청 세션 토큰 갱신(만료된 access token 을 refresh 해 쿠키에 다시 쓴다). 보호 경로 리다이렉트는 하지 않는다 — 비로그인 /saved 는 안내 판(시안). */
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  // 키 미설정이면 세션 갱신 건너뜀 — 02 Task 2 전 로컬. 운영에서는 조용히 비로그인으로 넘어가지 않는다.
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (process.env.NODE_ENV === "production") throw new Error("NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
    if (!warned) { warned = true; console.warn("[proxy] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정 — 세션 갱신 건너뜀"); }
    return response;
  }
  const supabase = createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookies: {
      getAll() { return request.cookies.getAll(); },
      setAll(cookiesToSet, headers?: Record<string, string>) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        Object.entries(headers ?? {}).forEach(([k, v]) => response.headers.set(k, v));   // 세션 쿠키 실린 응답은 캐시 금지
      },
    },
  });
  await supabase.auth.getUser();   // 갱신 트리거. 반환값은 안 쓴다
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg|opengraph-image|sitemap.xml|robots.txt|api/|.*\\.(?:png|jpg|svg|webp)$).*)"],
};
```
- [x] **Step 4: auth 헬퍼**
```ts
// frontend/src/lib/auth.ts
import "server-only";
import { cache } from "react";
import type { NavUser } from "@/components/Nav";
import { getServerSupabase } from "@/lib/supabase/server";

export type SessionUser = { id: string; email: string };

let warned = false;

/** 서버에서 현재 사용자. getUser 는 토큰을 서버에서 검증한다(getSession 은 쿠키를 믿는다 — 쓰지 않는다). react cache 로 요청당 1번만 호출한다. */
export const getSessionUser = cache(async (): Promise<SessionUser | null> => {
  // 키 미설정이면 비로그인으로 — 02 Task 2 전 로컬. 운영에서는 조용히 비로그인으로 넘어가지 않는다.
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (process.env.NODE_ENV === "production") throw new Error("NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
    if (!warned) { warned = true; console.warn("[auth] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정 — 비로그인으로 동작"); }
    return null;
  }
  const supabase = await getServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  return user?.email ? { id: user.id, email: user.email } : null;
});

/** Nav 가 받는 모양. 저장한 회사·검토 건수는 03 에서 채운다. */
export async function getNavUser(): Promise<NavUser | null> {
  const u = await getSessionUser();
  return u ? { email: u.email, savedCompanies: [], reviewedCount: 0 } : null;
}
```
- [x] **Step 5: 타입·빌드** — `cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json; echo $?` → 0. `npm run build 2>&1 | tail -3` → 성공(proxy 가 `ƒ Proxy` 로 잡힌다).
- [x] **Step 6: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/lib/supabase frontend/src/proxy.ts frontend/src/lib/auth.ts && git commit -m "feat(renewal): Supabase 브라우저·서버 클라이언트, proxy 세션 갱신, getSessionUser/getNavUser"
```

---

### Task 5: `(renewal)` 레이아웃 · Nav 손질 · `/dev/foundation` 이동

**Files:**
- Create: `frontend/src/app/(renewal)/layout.tsx`
- Move: `frontend/src/app/dev/foundation/{page,sheet}.tsx` → `frontend/src/app/(renewal)/dev/foundation/`
- Modify: `frontend/src/components/Nav.tsx`, `frontend/scripts/check_foundation.py`

- [x] **Step 1: 레이아웃**
```tsx
// frontend/src/app/(renewal)/layout.tsx
import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
import { SiteFooter } from "@/components/SiteFooter";
import { getNavUser } from "@/lib/auth";

/** 리뉴얼 페이지 공용 — 바닥(paper) + Nav(세션) + 바닥글. 옛 페이지는 09 컷오버에서 이 아래로 옮긴다. */
export default async function RenewalLayout({ children }: { children: ReactNode }) {
  const user = await getNavUser();
  return (
    <div className="rn min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1120px] px-5 pb-[120px]">
        <Nav user={user} />
        {children}
        <SiteFooter />
      </div>
    </div>
  );
}
```
- [x] **Step 2: `/dev/foundation` 이동** — `git mv frontend/src/app/dev frontend/src/app/\(renewal\)/dev`. `page.tsx` 에서 `Nav`·`SiteFooter` import 와 두 JSX, 바깥 두 `<div>` 래퍼를 제거하고 fragment(`<>…</>`)로 감싼다. `Nav` 의 가짜 `user` 는 없어진다(레이아웃이 실제 세션을 넣는다) — 로그인 전이면 "로그인" 링크가 보인다.
- [x] **Step 3: Nav 손질** — 전체 교체
```tsx
// frontend/src/components/Nav.tsx
"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Lockup } from "@/components/Logo";
import { cn } from "@/lib/utils";

export type NavUser = {
  email: string;
  savedCompanies: { bizrnoNorm: string; name: string }[];
  reviewedCount: number;
};

const LINKS = [
  { href: "/recommendations", label: "추천", match: /^\/(recommendations|companies\/[0-9])/ },
  { href: "/saved", label: "검토함", match: /^\/saved/ },
  { href: "/changelog", label: "개선 기록", match: /^\/changelog/ },
];

/** 로그인 링크 — 현재 경로 + 쿼리를 next 로. useSearchParams 는 Suspense 경계가 필요하다(Next 16). */
function LoginLink() {
  const pathname = usePathname() ?? "/";
  const search = useSearchParams()?.toString();
  const next = search ? `${pathname}?${search}` : pathname;
  return <Link href={`/login?next=${encodeURIComponent(next)}`} className="text-ink border-b border-ink">로그인</Link>;
}

/** 상단 nav — 비로그인 '로그인' / 로그인됨 you@… + 팝오버(저장한 회사 ★ · 검토함 · 설정 · 로그아웃). 링크 묶음이라 role=menu 는 쓰지 않는다. */
export function Nav({ user, signOutHref = "/logout" }: { user?: NavUser | null; signOutHref?: string }) {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); trigger.current?.focus(); } };
    addEventListener("click", close); addEventListener("keydown", esc);
    return () => { removeEventListener("click", close); removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div className="flex items-center justify-between py-[22px] text-[13px] text-ink-g">
      <Link href="/" aria-label="조달핏 홈"><Lockup /></Link>
      <nav className="flex items-center gap-[22px]" aria-label="주 메뉴">
        {LINKS.map((l) => {
          const active = l.match.test(pathname);
          return (
            <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined}
              className={cn("max-sm:hidden", active && "text-ink font-semibold max-sm:inline")}>
              {l.label}
            </Link>
          );
        })}
        {user ? (
          <div ref={ref} className="relative">
            <button ref={trigger} type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="nav-user-menu"
              className="text-ink font-semibold border-b border-ink cursor-pointer">
              {user.email.split("@")[0]}@…
            </button>
            {open && (
              <div id="nav-user-menu" data-menu className="absolute right-0 top-7 z-20 min-w-[240px] rounded-[10px] border border-hair bg-panel p-1.5 text-left font-normal shadow-[0_8px_24px_rgba(20,20,20,.06)] max-sm:-right-2">
                <div className="px-3 py-2 text-[13.5px] text-ink">{user.email}<small className="block text-[12px] text-ink-mute">로그인됨</small></div>
                <div className="my-1.5 h-px bg-rule" />
                <span className="t-k block px-3 pb-0.5 pt-2">저장한 회사 {user.savedCompanies.length}</span>
                {user.savedCompanies.map((c) => (
                  <Link key={c.bizrnoNorm} href={`/companies/${c.bizrnoNorm}`}
                    className="block rounded-md px-3 py-[7px] text-[13.5px] text-ink hover:bg-paper before:mr-2 before:text-[11px] before:text-orange before:content-['★']">
                    {c.name}
                  </Link>
                ))}
                <div className="my-1.5 h-px bg-rule" />
                <Link href="/saved" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  검토함<small className="block text-[12px] text-ink-mute">검토한 공고 {user.reviewedCount}건</small>
                </Link>
                <Link href="/settings" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  설정<small className="block text-[12px] text-ink-mute">비밀번호 변경 · 알림 수신 · 탈퇴</small>
                </Link>
                <div className="my-1.5 h-px bg-rule" />
                <a href={signOutHref} className="block rounded-md px-3 py-2 text-[13.5px] text-ink-mute hover:bg-paper">로그아웃</a>
              </div>
            )}
          </div>
        ) : (
          <Suspense fallback={<span className="text-ink border-b border-ink">로그인</span>}><LoginLink /></Suspense>
        )}
      </nav>
    </div>
  );
}
```
  (로그아웃은 `<a href>` — 라우트 핸들러가 쿠키를 지우고 `/` 로 보낸다. Next `Link` 프리페치가 로그아웃을 미리 실행하면 안 되므로 일부러 `<a>`.)
- [x] **Step 4: 검증 스크립트 갱신** — `frontend/scripts/check_foundation.py` 에서 `m = pg.evaluate("document.querySelectorAll('[role=menu] [role=menuitem]').length"); assert m == 5, m` → `m = pg.evaluate("document.querySelectorAll('[data-menu] a').length"); assert m == 5, m` 로, `assert pg.evaluate("!document.querySelector('[role=menu]')")` → `assert pg.evaluate("!document.querySelector('[data-menu]')")`. 그리고 이 페이지는 이제 **비로그인**으로 렌더되므로 메뉴 검사는 로그인 뒤 페이지(Task 10 `check_auth.py`)로 옮기고, 여기서는 `me` 조건을 `login: !!document.querySelector('a[href^="/login?next="]')` 로 바꾼다 — 메뉴 클릭·Escape·`m == 5` 세 줄과 390 의 `me` 를 삭제하고 `gateBtns == 2` 는 **nav 의 로그인 링크까지 3** 이 되므로 `a[href^="/login"], a[href^="/signup"]` 를 `.hairline a[href^="/login"], .hairline a[href^="/signup"]` 로 좁힌다. 01 계획 문서 Task 10 블록도 같은 내용으로.
- [x] **Step 5: 확인** — `npm run lint && npx tsc --noEmit -p tsconfig.json && npm run build 2>&1 | tail -3`; 개발 서버(`npm run dev -- --port 3001`) 띄우고 `FOUNDATION_URL=http://localhost:3001/dev/foundation uv run --no-sync python ../frontend/scripts/check_foundation.py` → ok.
- [x] **Step 6: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add -A frontend/src/app frontend/src/components/Nav.tsx frontend/scripts/check_foundation.py docs/superpowers/plans/2026-10-19-renewal-01-foundation.md && git commit -m "feat(renewal): (renewal) 레이아웃(세션 Nav), /dev/foundation 이동, Nav 로그인 링크에 쿼리·팝오버 role 제거·포커스 복귀"
```

---

### Task 6: 폼 부품 — Field · Consent · Narrow

**Files:**
- Create: `frontend/src/components/Field.tsx`, `frontend/src/components/Consent.tsx`, `frontend/src/components/Narrow.tsx`

- [x] **Step 1: Field**
```tsx
// frontend/src/components/Field.tsx
"use client";

import { useId, useState, type ComponentProps, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const INPUT = "h-[46px] w-full rounded-[8px] border border-field bg-panel px-3.5 text-[16px] text-ink outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-ph focus:border-orange focus:shadow-[0_0_0_4px_var(--color-orange-ring)] disabled:bg-paper disabled:text-ink-mute";

export function TextField({ label, hint, right, className, id, ...input }: { label: ReactNode; hint?: ReactNode; right?: ReactNode; className?: string } & ComponentProps<"input">) {
  const auto = useId(); const inputId = id ?? auto;
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between"><label htmlFor={inputId} className="t-k">{label}</label>{right}</div>
      <input id={inputId} className={INPUT} {...input} />
      {hint && <div className="mt-1.5 text-[12.5px] leading-[1.55] text-ink-dim">{hint}</div>}
    </div>
  );
}

/** 비밀번호 — 오른쪽 '표시/숨김'. 8자 미만일 때만 "8자 이상" 힌트(주황 괘선). */
export function PasswordField({ label = "비밀번호", min = 8, showMinHint = true, right, className, id, value, ...input }: { label?: ReactNode; min?: number; showMinHint?: boolean; right?: ReactNode; className?: string; value: string } & Omit<ComponentProps<"input">, "type" | "value">) {
  const auto = useId(); const inputId = id ?? auto;
  const [show, setShow] = useState(false);
  const short = showMinHint && value.length > 0 && value.length < min;
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between"><label htmlFor={inputId} className="t-k">{label}</label>{right}</div>
      <div className="relative">
        <input id={inputId} type={show ? "text" : "password"} value={value} className={cn(INPUT, "pr-14")} {...input} />
        <button type="button" onClick={() => setShow((v) => !v)} aria-pressed={show} aria-controls={inputId}
          className="absolute right-3 top-1/2 -translate-y-1/2 border-b border-line text-[12.5px] text-ink-g">{show ? "숨김" : "표시"}</button>
      </div>
      {short && <div className="mt-1.5 border-l-2 border-orange pl-2 text-[12.5px] text-ink">{min}자 이상</div>}
    </div>
  );
}
```
- [x] **Step 2: Consent**
```tsx
// frontend/src/components/Consent.tsx
"use client";

import Link from "next/link";

export type ConsentValue = { terms: boolean; privacy: boolean; marketing: boolean };
export const NO_CONSENT: ConsentValue = { terms: false, privacy: false, marketing: false };
export const requiredConsented = (c: ConsentValue) => c.terms && c.privacy;

/** 가입 동의 — 이용약관(필수) · 개인정보(필수) · 알림 메일(선택). 문구는 시안 gen_login.py::consent. */
export function Consent({ value, onChange, idPrefix = "consent" }: { value: ConsentValue; onChange: (v: ConsentValue) => void; idPrefix?: string }) {
  const row = "flex cursor-pointer items-start gap-2 text-[13px] leading-[1.55] text-ink-body";
  const box = "mt-[3px] accent-ink";
  return (
    <div className="my-4 flex flex-col gap-2">
      <label htmlFor={`${idPrefix}-terms`} className={row}>
        <input id={`${idPrefix}-terms`} type="checkbox" className={box} checked={value.terms} onChange={(e) => onChange({ ...value, terms: e.target.checked })} />
        <span><b className="font-semibold">[필수]</b> <Link href="/terms" target="_blank" className="u-link">이용약관</Link> 동의</span>
      </label>
      <label htmlFor={`${idPrefix}-privacy`} className={row}>
        <input id={`${idPrefix}-privacy`} type="checkbox" className={box} checked={value.privacy} onChange={(e) => onChange({ ...value, privacy: e.target.checked })} />
        <span><b className="font-semibold">[필수]</b> 개인정보 수집·이용 동의 — 이메일 주소 · 로그인·검토함·저장한 회사 보관 · 탈퇴 시 삭제. <Link href="/privacy" target="_blank" className="u-link">처리방침</Link></span>
      </label>
      <label htmlFor={`${idPrefix}-marketing`} className={`${row} text-ink-g`}>
        <input id={`${idPrefix}-marketing`} type="checkbox" className={box} checked={value.marketing} onChange={(e) => onChange({ ...value, marketing: e.target.checked })} />
        <span><span className="t-k mr-1.5">[선택]</span>알림 메일 수신 동의 — 준비 중, 시작 시 안내</span>
      </label>
    </div>
  );
}
```
- [x] **Step 3: Narrow**
```tsx
// frontend/src/components/Narrow.tsx
import type { ReactNode } from "react";
import { Panel } from "@/components/Panel";

/** 로그인·가입·재설정의 좁은 판 — 520px, 제목 28. 머리말(lead) 없음(문구 결정: 미사여구 제거). */
export function Narrow({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto mt-12 max-w-[520px] max-sm:mt-5">
      <h1 className="m-0 mb-3 text-[28px] font-semibold tracking-[-0.03em] text-ink max-sm:text-[22px]">{title}</h1>
      <Panel className="px-7 pb-7 pt-[26px] max-sm:px-4 max-sm:pb-[22px] max-sm:pt-5">{children}</Panel>
    </div>
  );
}
```
- [x] **Step 4: 타입** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0
- [x] **Step 5: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Field.tsx frontend/src/components/Consent.tsx frontend/src/components/Narrow.tsx && git commit -m "feat(renewal): 폼 부품 TextField·PasswordField·Consent·Narrow"
```

---

### Task 7: 로그인 · 회원가입 · 보냄 · 재설정 · 새 비밀번호 · 로그아웃 · 확인 라우트

**Files:**
- Create: `frontend/src/app/(renewal)/login/page.tsx`, `LoginForm.tsx`; `(renewal)/signup/page.tsx`, `SignupForm.tsx`; `(renewal)/signup/sent/page.tsx`, `ResendButton.tsx`; `(renewal)/reset/page.tsx`, `ResetForm.tsx`; `(renewal)/reset/new/page.tsx`, `NewPasswordForm.tsx`; `frontend/src/app/auth/confirm/route.ts`; `frontend/src/app/logout/route.ts`

- [x] **Step 1: 로그인**
```tsx
// frontend/src/app/(renewal)/login/page.tsx
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "로그인 | 조달핏", robots: { index: false, follow: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }) {
  const p = await searchParams;
  const next = safeNext(p.next);
  if (await getSessionUser()) redirect(next);
  return (
    <Narrow title="로그인">
      <LoginForm next={next} linkError={p.error === "link"} />
    </Narrow>
  );
}
```
```tsx
// frontend/src/app/(renewal)/login/LoginForm.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/Btn";
import { PasswordField, TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

const MSG: Record<string, string> = {
  invalid_credentials: "이메일 또는 비밀번호가 맞지 않습니다",
  email_not_confirmed: "이메일 확인 전입니다. 메일의 링크를 열면 로그인됩니다",
};

export function LoginForm({ next, linkError }: { next: string; linkError?: boolean }) {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = /.+@.+\..+/.test(email) && pw.length > 0 && !busy;

  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const { error } = await getBrowserSupabase().auth.signInWithPassword({ email, password: pw });
    if (error) { setErr(MSG[error.code ?? ""] ?? "로그인하지 못했습니다. 잠시 후 다시"); setBusy(false); return; }
    router.replace(next); router.refresh();
  }

  return (
    <form onSubmit={submit} noValidate>
      {linkError && <p className="mb-4 border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink-g"><b className="font-semibold text-ink">링크가 만료되었거나 이미 사용되었습니다.</b> 링크는 60분 동안 한 번만 유효합니다. 가입 확인은 <Link href="/signup" className="u-link text-ink">다시 가입</Link>, 비밀번호는 <Link href="/reset" className="u-link text-ink">재설정</Link>.</p>}
      <TextField label="이메일" type="email" autoComplete="email" inputMode="email" placeholder="you@company.co.kr" value={email} onChange={(e) => setEmail(e.target.value)} />
      <PasswordField className="mt-3.5" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" placeholder="비밀번호" showMinHint={false}
        right={<Link href={`/reset${email ? `?email=${encodeURIComponent(email)}` : ""}`} className="u-link text-[12.5px] text-ink-g">비밀번호 찾기</Link>} />
      {err && <p role="alert" className="mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">로그인</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href={`/signup?next=${encodeURIComponent(next)}`} className="u-link text-ink">회원가입</Link></div>
      <div className="mt-[22px] border-t border-rule pt-4">
        <span className="t-k mb-2 block">로그인하면</span>
        <ul className="m-0 list-none p-0 text-[14px] leading-[1.6]">
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">결과 전부</b><span>상위 5건 뒤의 나머지 공고</span></li>
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">검토함</b><span>검토 표시한 공고 보관</span></li>
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">저장한 회사</b><span>여러 회사 저장, 바로 결과</span></li>
        </ul>
      </div>
    </form>
  );
}
```
- [x] **Step 2: 회원가입**
```tsx
// frontend/src/app/(renewal)/signup/page.tsx
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { SignupForm } from "./SignupForm";

export const metadata: Metadata = { title: "회원가입 | 조달핏", robots: { index: false, follow: false } };

export default async function SignupPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const next = safeNext((await searchParams).next);
  if (await getSessionUser()) redirect(next);
  return <Narrow title="회원가입"><SignupForm next={next} /></Narrow>;
}
```
```tsx
// frontend/src/app/(renewal)/signup/SignupForm.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/Btn";
import { Consent, NO_CONSENT, requiredConsented, type ConsentValue } from "@/components/Consent";
import { PasswordField, TextField } from "@/components/Field";
import { PRIVACY_VERSION } from "@/lib/privacy";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { TERMS_VERSION } from "@/lib/terms";

export function SignupForm({ next }: { next: string }) {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [consent, setConsent] = useState<ConsentValue>(NO_CONSENT);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = /.+@.+\..+/.test(email) && pw.length >= 8 && requiredConsented(consent) && !busy;

  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const redirectTo = `${location.origin}/auth/confirm?next=${encodeURIComponent(next)}`;
    const { error } = await getBrowserSupabase().auth.signUp({
      email, password: pw,
      options: { emailRedirectTo: redirectTo, data: { terms_version: TERMS_VERSION, privacy_version: PRIVACY_VERSION, marketing_opt_in: consent.marketing } },
    });
    // consented_at 은 클라이언트가 보내지 않는다 — 0052 트리거가 서버 시각으로 찍는다(서버 시각이 기록의 진실값).
    // 계정 존재 여부를 알리지 않는다(열거 방지) — Confirm email ON 이면 기존 계정에도 성공처럼 돌아오므로 같은 안내로 보낸다.
    if (error) { setErr("가입하지 못했습니다. 잠시 후 다시"); setBusy(false); return; }
    router.push(`/signup/sent?email=${encodeURIComponent(email)}&next=${encodeURIComponent(next)}`);
  }

  return (
    <form onSubmit={submit} noValidate>
      <TextField label="이메일" type="email" autoComplete="email" inputMode="email" placeholder="you@company.co.kr" value={email} onChange={(e) => setEmail(e.target.value)} hint="확인 메일 발송" />
      <PasswordField className="mt-3.5" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" placeholder="8자 이상" />
      <Consent value={consent} onChange={setConsent} />
      {err && <p role="alert" className="mb-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="h-[46px] w-full text-[15px]">가입</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href={`/login?next=${encodeURIComponent(next)}`} className="u-link text-ink">로그인</Link></div>
    </form>
  );
}
```
- [x] **Step 3: 확인 메일 보냄**
```tsx
// frontend/src/app/(renewal)/signup/sent/page.tsx
import type { Metadata } from "next";
import { Narrow } from "@/components/Narrow";
import { safeNext } from "@/lib/safe-next";
import { ResendButton } from "./ResendButton";

export const metadata: Metadata = { title: "회원가입 | 조달핏", robots: { index: false, follow: false } };

export default async function SentPage({ searchParams }: { searchParams: Promise<{ email?: string; next?: string; kind?: string }> }) {
  const p = await searchParams; const email = p.email ?? ""; const next = safeNext(p.next);
  const recovery = p.kind === "recovery";
  return (
    <Narrow title={recovery ? "비밀번호 재설정" : "회원가입"}>
      <h2 className="m-0 mb-2 text-[20px] font-semibold tracking-[-0.02em]">{recovery ? "재설정 링크를 보냈습니다" : "확인 메일을 보냈습니다"}</h2>
      <p className="m-0 text-[14.5px] leading-[1.65] text-ink-body">{recovery ? "메일의 링크를 열면 새 비밀번호를 정합니다." : "메일의 링크를 열면 가입이 완료됩니다."}</p>
      <ul className="m-0 mt-[18px] list-none p-0 text-[14px] leading-[1.6]">
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">받는 곳</span><b className="border-b-2 border-orange font-semibold">{email || "—"}</b></li>
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">유효</span><span>60분 · 1회</span></li>
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">안 오면</span><span>스팸함 확인 · 보낸 주소 <b className="font-semibold">noreply@jodalfit.co.kr</b></span></li>
      </ul>
      <div className="mt-[18px] flex flex-wrap items-center gap-4 text-[13.5px]">
        {email && <ResendButton email={email} next={next} kind={recovery ? "recovery" : "signup"} />}
        <a href={recovery ? "/reset" : `/signup?next=${encodeURIComponent(next)}`} className="u-link text-ink">다른 이메일</a>
      </div>
    </Narrow>
  );
}
```
```tsx
// frontend/src/app/(renewal)/signup/sent/ResendButton.tsx
"use client";

import { useEffect, useState } from "react";
import { getBrowserSupabase } from "@/lib/supabase/browser";

/** 다시 보내기 — 60초 뒤 활성. signup 은 auth.resend, recovery 는 resetPasswordForEmail 재호출. */
export function ResendButton({ email, next, kind }: { email: string; next: string; kind: "signup" | "recovery" }) {
  const [left, setLeft] = useState(60); const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const [sentCount, setSentCount] = useState(0);
  useEffect(() => { if (left <= 0) return; const t = setTimeout(() => setLeft((s) => s - 1), 1000); return () => clearTimeout(t); }, [left]);
  async function resend() {
    setState("busy");
    const sb = getBrowserSupabase();
    const redirectTo = `${location.origin}/auth/confirm?next=${encodeURIComponent(kind === "recovery" ? "/reset/new" : next)}`;
    const { error } = kind === "signup" ? await sb.auth.resend({ type: "signup", email, options: { emailRedirectTo: redirectTo } }) : await sb.auth.resetPasswordForEmail(email, { redirectTo });
    if (!error) setSentCount((c) => c + 1);
    setState(error ? "error" : "idle"); setLeft(60);
  }
  if (left > 0) return <span className="text-ink-mute">{sentCount > 0 && <span className="text-ink-g">다시 보냈습니다 · </span>}다시 보내기 — {left}초 뒤</span>;
  return <button type="button" onClick={resend} disabled={state === "busy"} className="u-link text-ink">{state === "error" ? "다시 보내기(실패, 재시도)" : "다시 보내기"}</button>;
}
```
- [x] **Step 4: 확인 라우트 · 로그아웃**
```ts
// frontend/src/app/auth/confirm/route.ts
import { NextResponse, type NextRequest } from "next/server";
import type { EmailOtpType } from "@supabase/supabase-js";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/safe-next";

let warned = false;

/** 메일 링크 — token_hash 를 세션으로 바꾸고 next 로. 실패는 /login?error=link. recovery 는 /reset/new 로 강제. */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const token_hash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type") as EmailOtpType | null;
  const next = type === "recovery" ? "/reset/new" : safeNext(url.searchParams.get("next"));
  if (!token_hash || !type) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (!warned) { warned = true; console.warn("[auth/confirm] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정"); }
    return NextResponse.redirect(new URL("/login?error=link", url.origin));
  }
  const supabase = await getServerSupabase({ strict: true });
  const { error } = await supabase.auth.verifyOtp({ token_hash, type });
  if (error) return NextResponse.redirect(new URL("/login?error=link", url.origin));
  const res = NextResponse.redirect(new URL(next, url.origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
```
```ts
// frontend/src/app/logout/route.ts
import { NextResponse, type NextRequest } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";

let warned = false;

/** 로그아웃 — 쿠키 세션 제거 후 홈. Nav 가 <a href="/logout"> 로 온다(프리페치 안 되게 Link 가 아님). */
export async function GET(req: NextRequest) {
  if (req.headers.get("sec-fetch-site") && req.headers.get("sec-fetch-site") !== "same-origin") return NextResponse.redirect(new URL("/", new URL(req.url).origin));
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    const supabase = await getServerSupabase({ strict: true });
    await supabase.auth.signOut();
  } else if (!warned) {
    warned = true; console.warn("[logout] NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 미설정");
  }
  const res = NextResponse.redirect(new URL("/?logout=1", new URL(req.url).origin));
  res.headers.set("Cache-Control", "no-store");
  return res;
}
```
  라우트 핸들러의 `setAll` 은 `cookies()` 에 쓰기가 가능하므로 세션 쿠키가 응답에 실린다.
- [x] **Step 5: 재설정 · 새 비밀번호**
```tsx
// frontend/src/app/(renewal)/reset/page.tsx
import type { Metadata } from "next";
import { Narrow } from "@/components/Narrow";
import { ResetForm } from "./ResetForm";

export const metadata: Metadata = { title: "비밀번호 재설정 | 조달핏", robots: { index: false, follow: false } };

export default async function ResetPage({ searchParams }: { searchParams: Promise<{ email?: string }> }) {
  return <Narrow title="비밀번호 재설정"><ResetForm initialEmail={(await searchParams).email ?? ""} /></Narrow>;
}
```
```tsx
// frontend/src/app/(renewal)/reset/ResetForm.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/Btn";
import { TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function ResetForm({ initialEmail }: { initialEmail: string }) {
  const router = useRouter();
  const [email, setEmail] = useState(initialEmail); const [busy, setBusy] = useState(false);
  const ok = /.+@.+\..+/.test(email) && !busy;
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true);
    await getBrowserSupabase().auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/auth/confirm?next=${encodeURIComponent("/reset/new")}` });
    // 존재하지 않는 이메일도 같은 화면으로(열거 방지)
    router.push(`/signup/sent?kind=recovery&email=${encodeURIComponent(email)}`);
  }
  return (
    <form onSubmit={submit} noValidate>
      <p className="mb-[18px] border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink-g">가입한 이메일로 재설정 링크를 보냅니다.</p>
      <TextField label="이메일" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">재설정 링크 받기</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href="/login" className="u-link text-ink">로그인</Link></div>
    </form>
  );
}
```
```tsx
// frontend/src/app/(renewal)/reset/new/page.tsx
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { NewPasswordForm } from "./NewPasswordForm";

export const metadata: Metadata = { title: "새 비밀번호 | 조달핏", robots: { index: false, follow: false } };

/** recovery 링크를 연 상태(세션 있음)에서만. 세션이 없으면 재설정 처음으로. */
export default async function NewPasswordPage() {
  const user = await getSessionUser();
  if (!user) redirect("/reset");
  return <Narrow title="새 비밀번호"><NewPasswordForm email={user.email} /></Narrow>;
}
```
```tsx
// frontend/src/app/(renewal)/reset/new/NewPasswordForm.tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/Btn";
import { PasswordField, TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function NewPasswordForm({ email }: { email: string }) {
  const router = useRouter();
  const [a, setA] = useState(""); const [b, setB] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = a.length >= 8 && a === b && !busy;
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const { error } = await getBrowserSupabase().auth.updateUser({ password: a });
    if (error) { setErr(error.code === "same_password" ? "이전과 같은 비밀번호입니다" : "변경하지 못했습니다. 링크를 다시 받기"); setBusy(false); return; }
    router.replace("/recommendations"); router.refresh();
  }
  return (
    <form onSubmit={submit} noValidate>
      <TextField label="계정" type="email" value={email} disabled readOnly />
      <PasswordField className="mt-3.5" label="새 비밀번호" value={a} onChange={(e) => setA(e.target.value)} autoComplete="new-password" placeholder="8자 이상" />
      <PasswordField className="mt-3.5" label="새 비밀번호 확인" value={b} onChange={(e) => setB(e.target.value)} autoComplete="new-password" placeholder="한 번 더" showMinHint={false} />
      {err && <p role="alert" className="mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">변경</Btn>
      <p className="mt-3.5 text-[12.5px] leading-[1.6] text-ink-dim">변경 시 다른 기기 로그인 해제.</p>
    </form>
  );
}
```
- [x] **Step 6: 확인** — `npm run lint && npx tsc --noEmit -p tsconfig.json; echo $?` → 0. 개발 서버에서 `/login` `/signup` `/signup/sent?email=a@b.c` `/reset` 이 뜨고, `/reset/new` 는 비로그인 시 `/reset` 으로, `/logout` 은 `/`로 간다(curl -I 로 302 확인).
- [x] **Step 7: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add "frontend/src/app/(renewal)/login" "frontend/src/app/(renewal)/signup" "frontend/src/app/(renewal)/reset" frontend/src/app/auth frontend/src/app/logout && git commit -m "feat(renewal): 로그인·회원가입·확인 메일·재설정·새 비밀번호·로그아웃 + /auth/confirm"
```

---

### Task 8: 0052 `user_consents` + 트리거

**Files:**
- Create: `supabase/migrations/0052_user_consents.sql`

- [x] **Step 1: 마이그레이션**
```sql
-- ====================================================================
-- 0052 user_consents — 가입 때 받은 동의 기록 (이용약관·개인정보 필수, 알림 메일 선택)
--
-- 가입 폼은 동의를 auth.signUp 의 user_metadata 로 보낸다(확인 전엔 세션이 없어 RLS 테이블에 직접 못 쓴다).
-- auth.users 에 행이 생길 때 트리거가 metadata 를 이 표로 옮긴다. consented_at 은 metadata 를 신뢰하지 않고
-- 트리거 실행 시각(서버 시각)을 찍는다 — 서버 시각이 기록의 진실값. 이후 metadata 가 바뀌어도 이 표는 그대로 —
-- "가입 당시 무엇에 동의했나"가 기록의 뜻이다. 알림 수신 변경은 나중 설정 페이지가 update 한다(별도 정책).
-- Dashboard SQL Editor 에서 실행 (CLI 아님).
-- ====================================================================

create table if not exists public.user_consents (
  user_id          uuid primary key references auth.users(id) on delete cascade,
  terms_version    text not null,
  privacy_version  text not null,
  marketing_opt_in boolean not null default false,
  consented_at     timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

comment on table public.user_consents is '가입 시 동의 기록. terms_version=lib/terms.ts TERMS_VERSION, privacy_version=lib/privacy.ts PRIVACY_VERSION.';

alter table public.user_consents enable row level security;

grant select, update (marketing_opt_in) on public.user_consents to authenticated;

drop policy if exists "own consent read" on public.user_consents;
create policy "own consent read" on public.user_consents
  for select using (auth.uid() = user_id);

drop policy if exists "own marketing_opt_in update" on public.user_consents;
create policy "own marketing_opt_in update" on public.user_consents
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create or replace function public.handle_new_user_consent()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_consents (user_id, terms_version, privacy_version, marketing_opt_in, consented_at)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'terms_version', ''),
    coalesce(new.raw_user_meta_data->>'privacy_version', ''),
    coalesce(nullif(new.raw_user_meta_data->>'marketing_opt_in', '') ~* '^(true|t|1)$', false),
    now()
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_consent on auth.users;
create trigger on_auth_user_created_consent
  after insert on auth.users
  for each row execute function public.handle_new_user_consent();

-- 동의 기록은 불변 — 설정 페이지가 바꿀 수 있는 것은 marketing_opt_in 뿐. updated_at 은 여기서 찍는다(0001 의 set_updated_at 관례).
create or replace function public.lock_consent_history()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.user_id <> old.user_id
     or new.terms_version <> old.terms_version
     or new.privacy_version <> old.privacy_version
     or new.consented_at <> old.consented_at then
    raise exception 'user_consents: user_id/terms_version/privacy_version/consented_at are immutable';
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_user_consents_lock_history on public.user_consents;
create trigger trg_user_consents_lock_history
  before update on public.user_consents
  for each row execute function public.lock_consent_history();
```
- [x] **Step 2: 적용** — Supabase Dashboard → SQL Editor 에 붙여 실행. 확인:
```sql
select tgname from pg_trigger where tgrelid = 'auth.users'::regclass and tgname = 'on_auth_user_created_consent';
select count(*) from public.user_consents;
```
- [x] **Step 3: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add supabase/migrations/0052_user_consents.sql && git commit -m "feat(db): 0052 user_consents + auth.users 트리거"
```

---

### Task 9: 스모크 — 메일 없이 확인·재설정 링크 왕복

**Files:**
- Create: `frontend/scripts/auth_smoke.mjs`

- [ ] **Step 1: 스크립트** — service_role 로 사용자 생성 → `admin.generateLink` 로 `hashed_token` 을 얻어 우리 `/auth/confirm` 을 직접 친다. 실제 메일은 안 보낸다.
```js
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
```
- [ ] **Step 2: 실행** — 개발 서버 3001: `cd C:/Dev/personal/jodalfit/frontend && AUTH_URL=http://localhost:3001 node --env-file=.env.local scripts/auth_smoke.mjs` → `ok auth smoke: …`. (`.env.local` 에 `SUPABASE_URL`·`SUPABASE_SERVICE_ROLE_KEY`·`NEXT_PUBLIC_SUPABASE_ANON_KEY` 가 이미 있다.) 실패 시 메시지가 어느 단계인지 말해 준다 — 1·4 가 실패하면 Task 1 Step 1~2(Confirm email, Redirect URL) 또는 Task 8 미적용.
- [x] **Step 3: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/scripts/auth_smoke.mjs && git commit -m "test(renewal): auth 스모크 — generateLink 로 확인·재설정 링크 왕복, 동의 트리거, 로그아웃"
```

---

### Task 10: `/terms` + 개인정보처리방침 개정

**Files:**
- Create: `frontend/src/app/(renewal)/terms/page.tsx`
- Modify: `frontend/src/app/privacy/page.tsx`, `frontend/src/lib/privacy.ts`

- [x] **Step 1: 이용약관(초안)** — 승우님 검토 뒤 시행일(`TERMS_VERSION`)을 확정한다. 문구는 공문 톤.
```tsx
// frontend/src/app/(renewal)/terms/page.tsx
import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { TERMS_VERSION } from "@/lib/terms";
import { CONTACT_EMAIL } from "@/lib/privacy";

export const metadata: Metadata = { title: "이용약관 | 조달핏", alternates: { canonical: "/terms" } };

const H = "mt-8 mb-2 text-[16px] font-semibold text-ink";
const P = "m-0 text-[14.5px] leading-[1.75] text-ink-body";
const L = "m-0 list-decimal pl-5 text-[14.5px] leading-[1.75] text-ink-body [&>li]:mt-1";

export default function TermsPage() {
  return (
    <>
      <PageHead title="이용약관" meta={[`시행 ${TERMS_VERSION}`]} />
      <Panel className="mt-[22px] pt-2">
        <h2 className={H}>제1조 (목적)</h2>
        <p className={P}>이 약관은 조달핏(이하 "서비스")이 제공하는 공공입찰 공고 추천 및 관련 정보 제공 서비스의 이용 조건과 절차, 이용자와 서비스 운영자의 권리·의무를 정합니다.</p>
        <h2 className={H}>제2조 (정의)</h2>
        <ol className={L}>
          <li>"이용자"란 이 약관에 동의하고 서비스를 이용하는 자를 말합니다.</li>
          <li>"계정"이란 이메일과 비밀번호로 식별되는 이용자 단위를 말합니다.</li>
          <li>"콘텐츠"란 서비스가 나라장터(국가종합전자조달) 등 공공데이터를 바탕으로 가공·표시하는 공고, 회사 정보, 추천 결과, 근거 설명을 말합니다.</li>
        </ol>
        <h2 className={H}>제3조 (약관의 효력과 변경)</h2>
        <ol className={L}>
          <li>이 약관은 서비스 화면에 게시함으로써 효력이 발생합니다.</li>
          <li>운영자는 관련 법령을 위반하지 않는 범위에서 약관을 변경할 수 있으며, 변경 시 시행일 7일 전부터 서비스 화면에 공지합니다. 이용자에게 불리한 변경은 30일 전에 공지합니다.</li>
          <li>이용자가 변경 약관 시행 후에도 서비스를 계속 이용하면 변경에 동의한 것으로 봅니다.</li>
        </ol>
        <h2 className={H}>제4조 (서비스의 내용)</h2>
        <ol className={L}>
          <li>서비스는 이용자가 입력한 회사명·사업자등록번호 또는 키워드를 기준으로 검토할 만한 공고를 추천하고, 추천 근거와 참가 자격 판정, 공고·회사 관련 정보를 표시합니다.</li>
          <li>추천은 검토 순서를 제안하는 것이며 낙찰 가능성을 예측하거나 보장하지 않습니다. 참가 자격 판정은 공고 필드(허용업종·지역·등록 마감)에 한하며, 입찰 서류상의 요건은 이용자가 원문에서 확인해야 합니다.</li>
          <li>콘텐츠의 원천은 공공데이터이며, 서비스는 매일 갱신하되 원천의 오류·지연에 대해 책임지지 않습니다.</li>
          <li>운영자는 서비스의 전부 또는 일부를 변경·중단할 수 있으며, 유료 기능을 도입할 경우 사전에 공지합니다.</li>
        </ol>
        <h2 className={H}>제5조 (계정)</h2>
        <ol className={L}>
          <li>계정은 이메일 확인을 거쳐 생성됩니다. 이용자는 정확한 이메일을 제공하고 비밀번호를 안전하게 관리할 책임이 있습니다.</li>
          <li>계정은 양도·대여할 수 없습니다.</li>
          <li>이용자는 언제든 탈퇴할 수 있으며, 탈퇴 시 계정과 저장한 회사·검토한 공고 기록은 삭제됩니다.</li>
        </ol>
        <h2 className={H}>제6조 (이용자의 의무)</h2>
        <ol className={L}>
          <li>자동화 수단으로 콘텐츠를 대량 수집하거나 서비스 운영을 방해하는 행위를 하지 않습니다.</li>
          <li>타인의 정보를 도용하거나 서비스를 법령에 위반하는 목적으로 이용하지 않습니다.</li>
          <li>운영자는 위 의무를 위반한 계정의 이용을 제한할 수 있습니다.</li>
        </ol>
        <h2 className={H}>제7조 (지식재산권)</h2>
        <p className={P}>서비스의 화면 구성, 추천 방식, 가공된 콘텐츠에 대한 권리는 운영자에게 있습니다. 공공데이터 원문의 권리는 해당 기관에 있으며, 이용자는 콘텐츠를 입찰 검토 목적으로 이용할 수 있습니다.</p>
        <h2 className={H}>제8조 (책임의 한계)</h2>
        <ol className={L}>
          <li>서비스는 무료로 제공되는 범위에서 "있는 그대로" 제공되며, 운영자는 콘텐츠의 정확성·완전성·특정 목적 적합성을 보증하지 않습니다.</li>
          <li>이용자가 서비스의 추천·판정을 근거로 내린 입찰 결정의 결과에 대해 운영자는 책임지지 않습니다.</li>
          <li>천재지변, 원천 데이터 제공 중단, 통신 장애 등 운영자가 통제할 수 없는 사유로 인한 손해에 대해 책임지지 않습니다.</li>
        </ol>
        <h2 className={H}>제9조 (개인정보)</h2>
        <p className={P}>개인정보의 수집·이용·보관은 <a href="/privacy" className="u-link text-ink">개인정보처리방침</a>에 따릅니다.</p>
        <h2 className={H}>제10조 (준거법과 분쟁)</h2>
        <p className={P}>이 약관은 대한민국 법령에 따르며, 서비스 이용과 관련한 분쟁은 운영자 소재지를 관할하는 법원을 제1심 관할 법원으로 합니다.</p>
        <h2 className={H}>부칙</h2>
        <p className={P}>이 약관은 {TERMS_VERSION}부터 시행합니다. 문의 {CONTACT_EMAIL}</p>
      </Panel>
    </>
  );
}
```
- [x] **Step 2: 개인정보처리방침 개정** — `frontend/src/app/privacy/page.tsx` 의 수집 항목 절(현재 "주간 메일 신청" 중심)에 **계정** 항목을 추가한다. 파일을 읽고 수집·이용 목적 표(또는 목록)가 있는 Section 안에 아래 세 줄을 같은 마크업 스타일로 넣는다:
  - 수집 항목: 이메일 주소, 비밀번호(해시로만 저장), 동의 기록(약관·개인정보처리방침 버전·알림 수신 여부·동의 시각), 저장한 회사·검토한 공고
  - 목적: 로그인과 계정 식별, 검토함·저장한 회사 보관, 동의 이력 보존
  - 보유 기간: 탈퇴 시 즉시 삭제(법령상 보존 의무가 있는 기록 제외). 로그인 기록은 1년.
  처리 위탁 절에 **Resend(메일 발송, 미국)** 를 추가한다(이미 Supabase·Vercel 등이 적혀 있으면 같은 형식). `frontend/src/lib/privacy.ts` 의 `PRIVACY_VERSION` 을 `"2026-10-19"` 로 올린다(가입 폼이 이 값을 동의 기록에 남긴다).
> **승우님 검토 항목(2026-10-19 검토에서 나온 것, 시행일 확정 전에 결정)**: ① 만 14세 미만 가입 제한(법정대리인 동의) 조항 추가 여부 — 이메일만으로 누구나 가입 가능한 구조. ② 제10조 전속 관할 — 이용자가 소비자로 해석되면 약관규제법 제14조상 무효 소지 → "민사소송법에 따른 관할"로 완화하거나 "사업자 대상 서비스" 명시. ③ (선택) 제5조 3항 탈퇴 시 삭제에 "로그인 기록 등 법령상 보존 자료 제외" 괄호. ④ 유료 전환 시 결제·환불 조항 개정 필요(지금은 없음).

- [x] **Step 3: 확인** — `/terms` 와 `/privacy` 가 뜨고, `npm run lint` 통과. `grep -rn "PRIVACY_VERSION" frontend/src` 에서 구독 폼(`subscribe.ts`)과 가입 폼이 같은 값을 쓰는지 본다.
- [x] **Step 4: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add "frontend/src/app/(renewal)/terms" frontend/src/app/privacy/page.tsx frontend/src/lib/privacy.ts && git commit -m "feat(renewal): 이용약관 초안(/terms) + 개인정보처리방침에 계정 항목·Resend 위탁, 버전 2026-10-19"
```

---

### Task 11: 화면 검증 `check_auth.py` + 수동 완주

**Files:**
- Create: `frontend/scripts/check_auth.py`

- [ ] **Step 1: 스크립트**
```python
# frontend/scripts/check_auth.py
"""로그인·가입·보냄·재설정·약관 화면 검증 — 금지어 0 · 인주 0 · 주황 면 0 · 버튼 활성 조건 · 390.
실행: cd backend && AUTH_URL=http://localhost:3001 uv run --no-sync python ../frontend/scripts/check_auth.py
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("AUTH_URL", "http://localhost:3000")
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "아침 7시", "주십시오"]
OUT = Path(__file__).resolve().parent
RULES = """() => { const cs = e => getComputedStyle(e); const all = [...document.querySelectorAll('body *')];
  return { orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    bg: cs(document.querySelector('.rn')).backgroundColor, h1: document.querySelector('h1') && cs(document.querySelector('h1')).fontSize } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, f"{pg.url} 금지어 {bad}"
    r = pg.evaluate(RULES); assert r["orangeFaces"] == 0 and not r["injuk"] and r["bg"] == "rgb(250, 249, 247)", (pg.url, r); return r

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None); pg = b.new_page(viewport={"width": 1280, "height": 900})
        dis = lambda: pg.evaluate("document.querySelector('form button[type=submit]').disabled")
        # 로그인 — 이메일·비밀번호 둘 다 있어야 켜짐, 비밀번호 표시 토글, 회원가입 링크에 next 유지
        pg.goto(f"{BASE}/login?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); r = rules(pg); assert r["h1"] == "28px", r
        assert dis(); pg.fill("input[type=email]", "you@company.co.kr"); assert dis(); pg.fill("input[type=password]", "x"); assert not dis()
        pg.click("button[aria-pressed]"); assert pg.evaluate("document.querySelector('input[autocomplete=current-password]').type") == "text"
        assert pg.evaluate("document.querySelector('a[href^=\"/signup?next=\"]').getAttribute('href')") == "/signup?next=%2Fsaved"
        assert pg.evaluate("!!document.querySelector('nav a[href^=\"/login?next=\"]')")   # 레이아웃의 비로그인 nav 링크
        pg.screenshot(path=str(OUT / "_shot_auth_login.png"), full_page=True)
        # 회원가입 — 8자 힌트, 필수 동의 둘 전엔 꺼짐
        pg.goto(f"{BASE}/signup?next=%2Fsaved"); pg.wait_for_load_state("networkidle"); rules(pg)
        pg.fill("input[type=email]", "you@company.co.kr"); pg.fill("input[type=password]", "short"); assert dis()
        assert pg.evaluate("!!document.querySelector('.border-l-2.border-orange')"), "8자 힌트 없음"
        pg.fill("input[type=password]", "longenough1"); assert dis()
        cb = pg.locator("input[type=checkbox]"); assert cb.count() == 3; cb.nth(0).check(); assert dis(); cb.nth(1).check(); assert not dis()
        pg.screenshot(path=str(OUT / "_shot_auth_signup.png"), full_page=True)
        # 보냄 — 이메일 강조 주황 밑줄, 다시 보내기 카운트다운
        pg.goto(f"{BASE}/signup/sent?email=you%40company.co.kr&next=%2Fsaved"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("getComputedStyle(document.querySelector('li b')).borderBottomColor") == "rgb(249, 115, 22)"
        assert "다시 보내기 — " in pg.evaluate("document.body.innerText")
        pg.screenshot(path=str(OUT / "_shot_auth_sent.png"), full_page=True)
        # 재설정 — 이메일 채워짐, 버튼 켜짐
        pg.goto(f"{BASE}/reset?email=you%40company.co.kr"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("document.querySelector('input[type=email]').value") == "you@company.co.kr" and not dis()
        # 새 비밀번호 — 비로그인은 /reset 으로
        pg.goto(f"{BASE}/reset/new"); pg.wait_for_load_state("networkidle"); assert pg.url.rstrip("/").endswith("/reset"), pg.url
        # 약관
        pg.goto(f"{BASE}/terms"); pg.wait_for_load_state("networkidle"); rules(pg)
        assert pg.evaluate("document.querySelectorAll('h2').length") >= 10
        pg.screenshot(path=str(OUT / "_shot_auth_terms.png"), full_page=True)
        # 390
        pg.set_viewport_size({"width": 390, "height": 844})
        for path in ("/login", "/signup", "/signup/sent?email=a%40b.c", "/reset", "/terms"):
            pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); assert not pg.evaluate("document.documentElement.scrollWidth > 390"), path
        pg.screenshot(path=str(OUT / "_shot_auth_390.png"), full_page=True)
        b.close()
    print("ok auth pages: login · signup · sent · reset · reset/new guard · terms · 390")

if __name__ == "__main__":
    sys.exit(main())
```
- [x] **Step 2: 실행** — `cd C:/Dev/personal/jodalfit/backend && AUTH_URL=http://localhost:3001 uv run --no-sync python ../frontend/scripts/check_auth.py` → ok. 실패가 컴포넌트 결함이면 스크립트를 느슨하게 하지 말고 고친다.
- [ ] **Step 3: 수동 완주(승우님 또는 실행자, 실제 메일)** — 프리뷰 또는 로컬에서: `/signup` 으로 실제 이메일 가입 → 받은 메일의 "이메일 확인" → `/dev/foundation` 등 next 로 돌아오고 nav 에 `you@…` → 메뉴 → 로그아웃 → `/login` 으로 다시 로그인 → `/reset` 으로 재설정 메일 → 링크 → `/reset/new` 에서 변경 → 새 비밀번호로 로그인. Resend 대시보드에서 메일 2통 발송 기록 확인. 결과를 README 기록에 한 줄로 남긴다(날짜·메일 도착 시간).
- [x] **Step 4: 커밋**
```bash
cd C:/Dev/personal/jodalfit && git add frontend/scripts/check_auth.py && git commit -m "test(renewal): 인증 화면 Playwright 검증"
```

---

### Task 12: 기록 · 푸시

**Files:**
- Modify: `docs/design/README.md`

- [x] **Step 1: README 끝에 추가**
```markdown
## 구현 — 02 auth (2026-10-xx, 브랜치 `renewal`)
Supabase Auth(이메일+비밀번호, Confirm email, OTP 60분) + Resend SMTP(`noreply@jodalfit.co.kr`). `@supabase/ssr` 쿠키 세션(`lib/supabase/{browser,server}.ts`, `src/proxy.ts`), `(renewal)` 레이아웃이 세션을 읽어 `Nav` 에 넣는다. 페이지 `/login` `/signup` `/signup/sent` `/reset` `/reset/new` `/terms`, 라우트 `/auth/confirm`(token_hash → 세션 → safeNext) `/logout`. 동의는 가입 metadata → 트리거 → `user_consents`(0052). 개인정보처리방침에 계정 항목·Resend 위탁 추가(버전 2026-10-19), 이용약관 초안(승우님 검토 후 시행일 확정).
검증: `scripts/auth_smoke.mjs`(generateLink 로 메일 없이 왕복) · `scripts/check_auth.py` · 실제 메일 완주 1회(날짜·소요).
남은 것: 설정 페이지(`/settings` 비밀번호 변경·알림 수신·탈퇴)는 03 또는 09 에서. `Nav` 로그인 링크 쿼리·팝오버 role 정리는 이 계획에서 반영.
최종 검토 반영: consented_at 서버 시각, authenticated 에 select·update(marketing_opt_in) grant, getSessionUser cache(), 운영에서 키 미설정이면 throw, GET /logout same-origin 확인. Supabase 설정에 Secure password change ON 추가.
```
- [x] **Step 2: 푸시**
```bash
cd C:/Dev/personal/jodalfit && git add docs/design/README.md && git commit -m "docs(design): 구현 02 auth 기록" && git push origin renewal
```

---

## 자체 검토

- 시안 장면 ↔ 태스크: 1 로그인(7) · 2 회원가입(7, 동의 6) · 3 확인 메일 보냄(7 sent + ResendButton) · 4 메일(1 템플릿) · 5 가입 완료 = 로그인됨(confirm 라우트 → next, Nav 세션 5; "가입 완료" 안내 한 줄은 03/05 결과 페이지에서) · 6 재설정 → 6a 보냄(sent?kind=recovery) → 6b 메일(템플릿) → 6c 새 비밀번호(7) · 7 로그아웃(logout 라우트) · 게이트 두 버튼(01 Gate, next 전달) · 만료 링크(login?error=link).
- 마스터 §3.2: 비밀번호 8자, 확인 메일 필수, 60분·1회(Task 1), `safeNext` 단일 함수(3, confirm·login·signup 이 씀), 세션 쿠키·proxy(4), 보호 경로 리다이렉트 없음(proxy 주석), 동의 세 가지 + 버전(6·8), 발신 주소·제목·본문(1), 이름·연락처 안 받음, 금지어(check_auth BANNED).
- §3.7 넘겨받은 것: Nav 쿼리·role·포커스·레이아웃 통합(5).
- 플레이스홀더: 약관은 초안이지만 완성 문장이고 검토 지점을 명시.
- 타입 일관: `NavUser` 는 01 그대로, `getNavUser` 가 그 모양을 돌려줌. `safeNext(raw, fallback)` 시그니처를 confirm·login·signup·sent 가 같게 씀. `ConsentValue{terms,privacy,marketing}` 를 SignupForm 이 metadata 로 변환. `PasswordField` 의 `value` 필수 prop 을 세 폼이 넘김.
- 열거 방지: 가입·재설정 모두 존재 여부와 무관하게 같은 "보냈습니다" 화면.
- 03 이 이어받는 접점: `getNavUser` 의 `savedCompanies`·`reviewedCount`, `user_consents.marketing_opt_in` update 정책(설정 페이지), `(renewal)` 레이아웃 아래 `/saved`.
