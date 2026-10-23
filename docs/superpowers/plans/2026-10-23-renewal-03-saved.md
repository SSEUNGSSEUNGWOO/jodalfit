# 리뉴얼 03 — saved: 저장한 회사(☆) · 검토한 공고 · 검토함 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 먼저 `2026-10-19-renewal-00-master.md` §3.1·§3.3·§3.5·§3.6 과 01·02 의 부품(`Nav` `Btn` `Panel` `PageHead` `Sheet` `Gate`)·`lib/auth.ts`·`lib/supabase/{browser,server}.ts` 를 읽는다. 시안: `docs/design/prototypes/final/saved-final.html`, 원천 `docs/design/scripts/gen_saved.py`, 결정 기록 `docs/design/README.md` "검토함 최종 시안".

**Goal:** 로그인한 사용자가 회사를 ☆ 로 저장하고 공고를 "검토"로 표시하면 계정에 남고, `/saved` 에서 공고(마감 순, 마감 지남은 회색 묶음)·저장한 회사(오늘 검토할 공고 수·이번 주 마감·가장 빠른 마감) 두 탭으로 본다. Nav 메뉴의 ★ 목록·검토함 건수가 실제 값으로 채워진다.

**Architecture:** 사용자 데이터는 RLS 테이블 둘(0054 `saved_companies`·`reviewed_notices`)에 **브라우저 Supabase 클라이언트(anon 키 + 세션 쿠키)** 가 직접 insert/delete 한다 — 라우트 핸들러·서버 액션 없음, 정책이 `auth.uid() = user_id` 를 강제하고 `user_id` 는 기본값 `auth.uid()`. 읽기는 서버 컴포넌트에서 `lib/saved.ts` 가 세션 클라이언트(`lib/supabase/server.ts`)로 사용자 행을 읽고, 공개 데이터(공고·회사·업종 수·추천 캐시)는 service_role 클라이언트(`lib/supabase-server.ts`)로 키 조인한다. 회사 행의 "오늘 N건·이번 주 마감·가장 빠른 마감"은 백엔드를 부르지 않고 `company_recommendations.payload` 캐시를 읽어 마감 지난 항목을 걷어낸 뒤 센다(캐시 없으면 `—`). 변경 뒤 `router.refresh()` 로 Nav 숫자·페이지를 다시 그린다. 05·06·07 은 여기서 만든 `StarCompany`·`ReviewButton` 을 그대로 꽂는다.

**Tech Stack:** Next.js 16.2(App Router, Server Components, `useRouter().refresh()`) · React 19 · `@supabase/ssr` 0.10 + `@supabase/supabase-js` 2(브라우저 클라이언트로 RLS 테이블 직접 쓰기) · Postgres RLS + pg_cron(0054) · Tailwind v4 토큰(01) · Playwright(backend venv) · `node --test`(순수 함수).

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `supabase/migrations/0054_saved.sql` | `saved_companies`·`reviewed_notices` 테이블, RLS 정책, grant, 마감 30일 지난 검토 행 주 1회 삭제(pg_cron) |
| `frontend/src/lib/saved-stats.ts` (+ `.test.ts`) | 순수 함수: 회사 행 숫자(`companyStats`), 근거 칩 고르기(`strongestWhy`) |
| `frontend/src/lib/saved.ts` | 서버 전용 읽기: `getNavSaved`(Nav 용), `getSavedCompanies`, `getReviewedNotices`, `getSavedCompanyKeys`, `getReviewedKeys` |
| `frontend/src/lib/auth.ts` | `getNavUser` 가 `getNavSaved` 로 ★ 목록·검토 건수를 채운다 |
| `frontend/src/components/StarCompany.tsx` | ☆ 회사 저장 / ★ 저장됨 토글(클라이언트). 비로그인이면 로그인 링크 |
| `frontend/src/components/ReviewButton.tsx` | 검토 / 검토함 토글(클라이언트). 비로그인이면 로그인 링크 |
| `frontend/src/app/(renewal)/saved/page.tsx` | `/saved` 서버 컴포넌트: 비로그인 안내 판 / 두 탭 데이터 조립 |
| `frontend/src/app/(renewal)/saved/SavedTabs.tsx` | 탭 전환(클라이언트, URL 반영 없음), PageHead 안 탭 + Panel |
| `frontend/src/app/(renewal)/saved/NoticeRows.tsx` | 공고 표(머리·행·해제/되돌리기·마감 지남 묶음) |
| `frontend/src/app/(renewal)/saved/CompanyRows.tsx` | 저장한 회사 표(머리·행·결과·★ 해제/되돌리기) |
| `frontend/src/app/(renewal)/dev/foundation/page.tsx`, `sheet.tsx` | 더미 ☆·검토 버튼을 실제 `StarCompany`·`ReviewButton` 으로(검증 스크립트가 여기서 저장 동작을 돌린다) |
| `frontend/scripts/check_saved.py` | Playwright 검증: 비로그인 판 → (키 있으면) 가입·로그인 → ☆·검토 → `/saved` 두 탭·해제·390 |
| `docs/design/README.md` | "구현 — 03 saved" 기록 |

---

### Task 1: 0054 `saved_companies` · `reviewed_notices` + RLS + 주 1회 정리

**Files:**
- Create: `supabase/migrations/0054_saved.sql`

- [x] **Step 1: 마이그레이션 파일**

```sql
-- supabase/migrations/0054_saved.sql
-- ====================================================================
-- 0054 saved_companies · reviewed_notices — 저장한 회사(☆)와 검토 표시한 공고 (리뉴얼 03)
--
-- 브라우저가 anon 키 + 세션 쿠키로 직접 insert/delete 한다. user_id 는 기본값 auth.uid() — 클라이언트는
-- user_id 를 보내지 않는다. 정책은 전부 auth.uid() = user_id. update 는 없다(토글은 insert/delete).
-- reviewed_notices.why 는 검토를 누른 순간의 근거 칩 한 개(예: "재출현 기관") — 검토함 둘째 줄에 그대로 보여 준다.
-- 마감 30일 지난 검토 행은 pg_cron 이 주 1회 지운다(시안 문구 "마감 30일 뒤 자동 정리").
-- Dashboard SQL Editor 에서 실행 (CLI 아님).
-- ====================================================================

create table if not exists public.saved_companies (
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  bizrno_norm text not null check (bizrno_norm ~ '^\d{10}$'),
  created_at  timestamptz not null default now(),
  primary key (user_id, bizrno_norm)
);
comment on table public.saved_companies is '사용자가 ☆ 로 저장한 회사. bizrno_norm = companies.bizrno_norm (10자리).';

create table if not exists public.reviewed_notices (
  user_id         uuid not null default auth.uid() references auth.users(id) on delete cascade,
  bid_ntce_no     text not null,
  bid_ntce_ord    text not null default '000',
  via_bizrno_norm text check (via_bizrno_norm is null or via_bizrno_norm ~ '^\d{10}$'),
  why             text,
  created_at      timestamptz not null default now(),
  primary key (user_id, bid_ntce_no, bid_ntce_ord)
);
comment on table public.reviewed_notices is '사용자가 검토 표시한 공고. via_bizrno_norm = 어느 회사 결과에서 검토했는지. why = 그때의 근거 칩.';

alter table public.saved_companies  enable row level security;
alter table public.reviewed_notices enable row level security;

grant select, insert, delete on public.saved_companies  to authenticated;
grant select, insert, delete on public.reviewed_notices to authenticated;

drop policy if exists "own saved_companies" on public.saved_companies;
create policy "own saved_companies" on public.saved_companies
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own reviewed_notices" on public.reviewed_notices;
create policy "own reviewed_notices" on public.reviewed_notices
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 마감 30일 지난 검토 행 삭제 — 매주 토요일 19:00 UTC(KST 일 04:00, 0040 의 로그 정리와 같은 시각대).
-- cron 세션에도 2분 statement_timeout 이 걸리므로 첫 문장은 항상 set statement_timeout = 0 (0026 관례).
select cron.unschedule(jobid) from cron.job where jobname = 'purge-reviewed-notices-expired';
select cron.schedule('purge-reviewed-notices-expired', '0 19 * * 6', $$
  set statement_timeout = 0;
  delete from public.reviewed_notices r
   using public.bid_notices n
   where n.bid_ntce_no = r.bid_ntce_no and n.bid_ntce_ord = r.bid_ntce_ord
     and n.bid_clse_date < current_date - 30;
$$);
```

- [x] **Step 2: 적용** — Supabase Dashboard → SQL Editor 에 파일 내용을 붙여 실행한다(0053 처럼 `backend/.env` 의 `DATABASE_URL` 로 psycopg 에서 실행해도 같다). 확인 쿼리:

```sql
select tablename, rowsecurity from pg_tables where tablename in ('saved_companies','reviewed_notices');
-- 둘 다 rowsecurity = true
select jobname, schedule from cron.job where jobname = 'purge-reviewed-notices-expired';
-- 1행
```

- [x] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add supabase/migrations/0054_saved.sql && git commit -m "feat(db): 0054 saved_companies·reviewed_notices + RLS + 마감 30일 지난 검토 행 주 1회 정리"
```

---

### Task 2: `lib/saved-stats.ts` — 회사 행 숫자 · 근거 칩 (순수 함수, TDD)

**Files:**
- Create: `frontend/src/lib/saved-stats.ts`
- Test: `frontend/src/lib/saved-stats.test.ts`

- [x] **Step 1: 실패하는 테스트**

```ts
// frontend/src/lib/saved-stats.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { companyStats, strongestWhy } from "./saved-stats.ts";

const today = new Date(2026, 9, 16); // 2026-10-16

test("companyStats: 마감 지난 것은 빼고, 7일 이내를 이번 주로, 가장 빠른 마감을 고른다", () => {
  const s = companyStats(["2026-10-20", "2026-11-25", "2026-10-10", null, "2026-10-23"], today);
  assert.deepEqual(s, { total: 3, week: 1, soonest: { days: 4, month: 10, day: 20 } });
});

test("companyStats: 결과가 없으면 0 과 null", () => {
  assert.deepEqual(companyStats([], today), { total: 0, week: 0, soonest: null });
});

test("strongestWhy: vector 를 빼고 양수 점수 중 최대의 label", () => {
  const w = strongestWhy([
    { key: "vector", label: "유사도 73%", points: 73 },
    { key: "region", label: "지역 매칭", points: 9 },
    { key: "institution", label: "재출현 기관", points: 12 },
    { key: "deadline_urgent", label: "마감 임박", points: -9 },
  ]);
  assert.equal(w, "재출현 기관");
});

test("strongestWhy: 양수 신호가 없으면 null", () => {
  assert.equal(strongestWhy([{ key: "vector", label: "유사도 50%", points: 50 }]), null);
  assert.equal(strongestWhy(undefined), null);
});
```

- [x] **Step 2: 실패 확인** — `cd C:/Dev/personal/jodalfit/frontend && node --experimental-strip-types --test src/lib/saved-stats.test.ts` → `Cannot find module` 로 실패.

- [x] **Step 3: 구현**

```ts
// frontend/src/lib/saved-stats.ts
// 검토함 회사 행의 숫자와 근거 칩 — 시안 gen_saved.py:91-92 (n = 결과 수, wk = D-7 이내, d = 가장 빠른 마감),
// gen_results_v2.py::strongest (vector 제외, points > 0 중 최대) 와 같은 규칙. 순수 함수 — node --test.
import { dLeft } from "@/lib/format";

export type DLeft = { days: number; month: number; day: number };
export type CompanyStats = { total: number; week: number; soonest: DLeft | null };

export function companyStats(clseDates: (string | null | undefined)[], today: Date = new Date()): CompanyStats {
  const ds = clseDates.map((d) => dLeft(d, today)).filter((x): x is DLeft => !!x && x.days >= 0);
  let soonest: DLeft | null = null;
  for (const x of ds) if (!soonest || x.days < soonest.days) soonest = x;
  return { total: ds.length, week: ds.filter((x) => x.days <= 7).length, soonest };
}

export type ScoreSignalLike = { key: string; label: string; points: number };

export function strongestWhy(breakdown: ScoreSignalLike[] | null | undefined): string | null {
  let best: ScoreSignalLike | null = null;
  for (const s of breakdown ?? []) {
    if (s.key === "vector" || s.points <= 0) continue;
    if (!best || s.points > best.points) best = s;
  }
  return best?.label ?? null;
}
```

- [x] **Step 4: 통과** — `node --experimental-strip-types --test src/lib/saved-stats.test.ts` → `# pass 4`. (`@/lib/format` 경로가 node 에서 안 풀리면 `../lib/format.ts` 가 아니라 `./format.ts` 로 상대 import 로 바꾼다 — `format.test.ts` 가 쓰는 방식을 따른다.)

- [x] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/lib/saved-stats.ts frontend/src/lib/saved-stats.test.ts && git commit -m "feat(renewal): saved-stats — 회사 행 숫자(companyStats)·근거 칩(strongestWhy) 순수 함수 + 테스트"
```

---

### Task 3: `lib/saved.ts` 서버 읽기 + `getNavUser` 채우기

**Files:**
- Create: `frontend/src/lib/saved.ts`
- Modify: `frontend/src/lib/auth.ts:25-29` (`getNavUser`)

- [x] **Step 1: `lib/saved.ts`**

```ts
// frontend/src/lib/saved.ts
// 검토함·Nav 가 읽는 사용자 데이터. 사용자 행은 세션 클라이언트(RLS), 공개 데이터 조인은 service_role.
// 비로그인(세션 없음)이면 사용자 테이블 select 가 권한 오류 → 전부 빈 값으로 돌려준다.
import "server-only";
import { cache } from "react";
import { getServerSupabase as getSessionSupabase } from "@/lib/supabase/server";
import { getServerSupabase as getPublicSupabase } from "@/lib/supabase-server";
import { SUMMARY_COLS, type NoticeSummary } from "@/lib/notice";
import { dLeft } from "@/lib/format";
import { companyStats, type CompanyStats, type DLeft } from "@/lib/saved-stats";

type SavedCompanyKey = { bizrno_norm: string; created_at: string };
type ReviewedKey = { bid_ntce_no: string; bid_ntce_ord: string; via_bizrno_norm: string | null; why: string | null; created_at: string };

const savedCompanyRows = cache(async (): Promise<SavedCompanyKey[]> => {
  const sb = await getSessionSupabase();
  const { data, error } = await sb.from("saved_companies").select("bizrno_norm,created_at").order("created_at", { ascending: false });
  return error ? [] : ((data ?? []) as SavedCompanyKey[]);
});

const reviewedRows = cache(async (): Promise<ReviewedKey[]> => {
  const sb = await getSessionSupabase();
  const { data, error } = await sb
    .from("reviewed_notices")
    .select("bid_ntce_no,bid_ntce_ord,via_bizrno_norm,why,created_at")
    .order("created_at", { ascending: false });
  return error ? [] : ((data ?? []) as ReviewedKey[]);
});

/** StarCompany 초기값용 — 현재 사용자가 저장한 bizrno_norm 집합 */
export async function getSavedCompanyKeys(): Promise<Set<string>> {
  return new Set((await savedCompanyRows()).map((r) => r.bizrno_norm));
}

/** ReviewButton 초기값용 — `${bid_ntce_no}-${bid_ntce_ord}` 집합 */
export async function getReviewedKeys(): Promise<Set<string>> {
  return new Set((await reviewedRows()).map((r) => `${r.bid_ntce_no}-${r.bid_ntce_ord}`));
}

type CompanyLite = { bizrno: string; bizrno_norm: string; corp_nm: string; rgn_nm: string | null };

async function companiesByNorm(norms: string[]): Promise<Map<string, CompanyLite>> {
  if (norms.length === 0) return new Map();
  const { data } = await getPublicSupabase().from("companies").select("bizrno,bizrno_norm,corp_nm,rgn_nm").in("bizrno_norm", norms);
  return new Map(((data ?? []) as CompanyLite[]).map((c) => [c.bizrno_norm, c]));
}

/** Nav 메뉴용 — ★ 목록(이름)과 검토 건수 */
export async function getNavSaved(): Promise<{ savedCompanies: { bizrnoNorm: string; name: string }[]; reviewedCount: number }> {
  const [saved, reviewed] = await Promise.all([savedCompanyRows(), reviewedRows()]);
  const cos = await companiesByNorm(saved.map((r) => r.bizrno_norm));
  return {
    savedCompanies: saved.map((r) => ({ bizrnoNorm: r.bizrno_norm, name: cos.get(r.bizrno_norm)?.corp_nm ?? r.bizrno_norm })),
    reviewedCount: reviewed.length,
  };
}

export type SavedCompanyRow = {
  bizrnoNorm: string;
  name: string;
  region: string | null; // rgn_nm 원문 — 표시는 rgnBase
  industries: number;
  stats: CompanyStats | null; // 추천 캐시 없으면 null
};

/** 검토함 "저장한 회사" 탭. 숫자는 company_recommendations 캐시(마감 지난 항목 제외)에서. */
export async function getSavedCompanies(today: Date = new Date()): Promise<SavedCompanyRow[]> {
  const saved = await savedCompanyRows();
  if (saved.length === 0) return [];
  const norms = saved.map((r) => r.bizrno_norm);
  const pub = getPublicSupabase();
  const [cos, ind, reco] = await Promise.all([
    companiesByNorm(norms),
    pub.from("company_industries").select("bizrno").in("bizrno", norms), // companies.bizrno 는 10자리 그대로라 norm 과 같다
    pub.from("company_recommendations").select("bizrno_norm,payload").in("bizrno_norm", norms),
  ]);
  const indCount = new Map<string, number>();
  for (const r of (ind.data ?? []) as { bizrno: string }[]) indCount.set(r.bizrno, (indCount.get(r.bizrno) ?? 0) + 1);
  const stats = new Map<string, CompanyStats>();
  for (const r of (reco.data ?? []) as { bizrno_norm: string; payload: { results?: { bid_clse_date?: string | null }[] } }[]) {
    stats.set(r.bizrno_norm, companyStats((r.payload?.results ?? []).map((x) => x.bid_clse_date), today));
  }
  return saved.map((r) => {
    const c = cos.get(r.bizrno_norm);
    return {
      bizrnoNorm: r.bizrno_norm,
      name: c?.corp_nm ?? r.bizrno_norm,
      region: c?.rgn_nm ?? null,
      industries: indCount.get(c?.bizrno ?? r.bizrno_norm) ?? 0,
      stats: stats.get(r.bizrno_norm) ?? null,
    };
  });
}

export type ReviewedNoticeRow = {
  no: string;
  ord: string;
  title: string;
  org: string;
  via: { bizrnoNorm: string; name: string } | null;
  why: string | null;
  clse: string | null;
  price: number | null;
  d: DLeft | null; // null = 마감 날짜 없음
};

/** 검토함 "공고" 탭. 진행 중(마감 오름차순)과 마감 지남(최근 순)을 나눠 준다. */
export async function getReviewedNotices(today: Date = new Date()): Promise<{ live: ReviewedNoticeRow[]; past: ReviewedNoticeRow[] }> {
  const reviewed = await reviewedRows();
  if (reviewed.length === 0) return { live: [], past: [] };
  const pub = getPublicSupabase();
  const [nt, cos] = await Promise.all([
    pub.from("bid_notices").select(SUMMARY_COLS).in("bid_ntce_no", [...new Set(reviewed.map((r) => r.bid_ntce_no))]),
    companiesByNorm([...new Set(reviewed.map((r) => r.via_bizrno_norm).filter((x): x is string => !!x))]),
  ]);
  const byKey = new Map(((nt.data ?? []) as NoticeSummary[]).map((n) => [`${n.bid_ntce_no}-${n.bid_ntce_ord}`, n]));
  const rows: ReviewedNoticeRow[] = [];
  for (const r of reviewed) {
    const n = byKey.get(`${r.bid_ntce_no}-${r.bid_ntce_ord}`);
    if (!n) continue; // 공고가 DB 에서 사라졌으면 표시하지 않는다(정리 잡이 지운다)
    const via = r.via_bizrno_norm ? cos.get(r.via_bizrno_norm) : undefined;
    rows.push({
      no: n.bid_ntce_no,
      ord: n.bid_ntce_ord,
      title: n.bid_ntce_nm,
      org: n.dmnd_instt_nm || n.ntce_instt_nm || "—",
      via: r.via_bizrno_norm ? { bizrnoNorm: r.via_bizrno_norm, name: via?.corp_nm ?? r.via_bizrno_norm } : null,
      why: r.why,
      clse: n.bid_clse_date ?? null,
      price: n.presmpt_prce ?? n.asign_bdgt_amt ?? null,
      d: dLeft(n.bid_clse_date, today),
    });
  }
  const live = rows.filter((x) => !x.d || x.d.days >= 0).sort((a, b) => (a.clse ?? "9999").localeCompare(b.clse ?? "9999"));
  const past = rows.filter((x) => x.d && x.d.days < 0).sort((a, b) => (b.clse ?? "").localeCompare(a.clse ?? ""));
  return { live, past };
}
```

`NoticeSummary` 의 필드명(`bid_ntce_nm`, `dmnd_instt_nm`, `ntce_instt_nm`, `bid_clse_date`, `presmpt_prce`, `asign_bdgt_amt`)은 `lib/notice.ts:356-371` 그대로다. 타입이 `string | null` 이 아니라 `string | undefined` 면 `?? null` 이 그대로 처리한다.

- [x] **Step 2: `getNavUser` 채우기** — `frontend/src/lib/auth.ts` 의 `getNavUser` 를 다음으로 교체한다(상단에 `import { getNavSaved } from "@/lib/saved";` 추가).

```ts
export async function getNavUser(): Promise<NavUser | null> {
  const u = await getSessionUser();
  if (!u) return null;
  const { savedCompanies, reviewedCount } = await getNavSaved();
  return { email: u.email, savedCompanies, reviewedCount };
}
```

- [x] **Step 3: 타입** — `cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json; echo $?` → 0. `lib/saved.ts` 가 `lib/auth.ts` 를 import 하지 않으므로 순환 없음.

- [x] **Step 4: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/lib/saved.ts frontend/src/lib/auth.ts && git commit -m "feat(renewal): lib/saved — 저장한 회사·검토한 공고 서버 읽기(세션 RLS + 공개 조인 + 추천 캐시 숫자), Nav ★ 목록·검토 건수 채움"
```

---

### Task 4: `StarCompany` · `ReviewButton` + `/dev/foundation` 에 실제 버튼

**Files:**
- Create: `frontend/src/components/StarCompany.tsx`, `frontend/src/components/ReviewButton.tsx`
- Modify: `frontend/src/app/(renewal)/dev/foundation/page.tsx:15,26`, `frontend/src/app/(renewal)/dev/foundation/sheet.tsx`

- [x] **Step 1: `StarCompany`**

```tsx
// frontend/src/components/StarCompany.tsx
// ☆ 회사 저장 / ★ 저장됨 — saved_companies 에 브라우저 클라이언트로 직접 insert/delete (RLS). 비로그인이면 로그인 링크.
// 시안(login-final 장면 5·README): ☆ 회색 → ★ 주황 테두리 "저장됨". 05 결과 머리·06 회사 머리가 이 부품을 PageHead aside 에 꽂는다.
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Btn } from "@/components/Btn";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

export function StarCompany({ bizrnoNorm, saved, loggedIn, className }: { bizrnoNorm: string; saved: boolean; loggedIn: boolean; className?: string }) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [on, setOn] = useState(saved);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();

  if (!loggedIn) {
    return (
      <Btn href={`/login?next=${encodeURIComponent(pathname)}`} className={className} data-star="guest">
        <span className="mr-1 text-ink-mute">☆</span>회사 저장
      </Btn>
    );
  }

  async function toggle() {
    if (busy) return;
    const next = !on;
    setOn(next);
    setBusy(true);
    const sb = getBrowserSupabase();
    const { error } = next
      ? await sb.from("saved_companies").insert({ bizrno_norm: bizrnoNorm })
      : await sb.from("saved_companies").delete().eq("bizrno_norm", bizrnoNorm);
    setBusy(false);
    if (error && error.code !== "23505") { setOn(!next); return; } // 23505 = 이미 저장됨 → 성공으로 본다
    start(() => router.refresh()); // Nav ★ 목록·검토함 숫자 갱신
  }

  return (
    <Btn variant={on ? "review" : "line"} onClick={toggle} aria-pressed={on} className={className} data-star={on ? "on" : "off"}>
      <span className={cn("mr-1", on ? "text-orange" : "text-ink-mute")}>{on ? "★" : "☆"}</span>
      {on ? "저장됨" : "회사 저장"}
    </Btn>
  );
}
```

- [x] **Step 2: `ReviewButton`**

```tsx
// frontend/src/components/ReviewButton.tsx
// 검토 / 검토함 — reviewed_notices 에 브라우저 클라이언트로 직접 insert/delete (RLS). 비로그인이면 로그인 링크.
// via = 어느 회사 결과에서 눌렀는지(bizrno_norm), why = 그 행의 근거 칩(strongestWhy) — 검토함 둘째 줄에 그대로 나온다.
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Btn } from "@/components/Btn";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function ReviewButton({ no, ord = "000", via = null, why = null, reviewed, loggedIn, onChange, className }: {
  no: string; ord?: string; via?: string | null; why?: string | null; reviewed: boolean; loggedIn: boolean;
  onChange?: (reviewed: boolean) => void; className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [on, setOn] = useState(reviewed);
  const [busy, setBusy] = useState(false);
  const [, start] = useTransition();

  if (!loggedIn) {
    return <Btn variant="review" href={`/login?next=${encodeURIComponent(pathname)}`} className={className} data-review="guest">검토</Btn>;
  }

  async function toggle() {
    if (busy) return;
    const next = !on;
    setOn(next);
    onChange?.(next);
    setBusy(true);
    const sb = getBrowserSupabase();
    const { error } = next
      ? await sb.from("reviewed_notices").insert({ bid_ntce_no: no, bid_ntce_ord: ord, via_bizrno_norm: via, why })
      : await sb.from("reviewed_notices").delete().eq("bid_ntce_no", no).eq("bid_ntce_ord", ord);
    setBusy(false);
    if (error && error.code !== "23505") { setOn(!next); onChange?.(!next); return; }
    start(() => router.refresh());
  }

  return (
    <Btn variant="review" on={on} onClick={toggle} aria-pressed={on} className={className} data-review={on ? "on" : "off"}>
      {on ? "검토함" : "검토"}
    </Btn>
  );
}
```

`Btn` 의 `review` 변형은 `data-on=true` 에서 `cursor-default` 가 걸리지만 클릭은 그대로 토글한다 — 결과 표에서 "검토함" 을 다시 누르면 해제. `onChange` 는 `SheetRow` 의 `reviewed`(왼쪽 주황 괘선)를 같이 바꾸려는 05 용 훅.

- [x] **Step 3: `/dev/foundation` 에 꽂기** — `page.tsx` 는 서버 컴포넌트다. 상단 import 에 `import { StarCompany } from "@/components/StarCompany";`, `import { getSessionUser } from "@/lib/auth";`, `import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";` 를 넣고, 함수를 `async` 로 바꿔 세션·키를 읽는다. 15행의 더미 ☆ 를 교체:

```tsx
export default async function FoundationPage() {
  const user = await getSessionUser();
  const [stars, reviews] = user ? await Promise.all([getSavedCompanyKeys(), getReviewedKeys()]) : [new Set<string>(), new Set<string>()];
  const loggedIn = !!user;
  // …
  <PageHead title="한종산업개발 주식회사" small={maskBizrno("1248177731")}
    aside={<StarCompany bizrnoNorm="1248177731" saved={stars.has("1248177731")} loggedIn={loggedIn} className="ml-3 h-[30px] text-[13px]" />}
    meta={["경상남도 창원시", "등록업종 15", "공급물품 없음", "기준일 2026-10-16"]} />
  // …
  <Sheet loggedIn={loggedIn} reviewed={[...reviews]} />
```

26행의 Btn 전시 줄에서 `<Btn variant="review">검토</Btn><Btn variant="review" on>검토함</Btn>` 은 그대로 둔다(변형 전시).

`sheet.tsx`: `ROWS` 세 건에 실제 공고 키를 붙인다 — `docs/design/data/sample.json` 의 `results[0..2]` 에서 `bid_ntce_no`·`bid_ntce_ord` 를 읽어 각 행에 `no_: "<bid_ntce_no>", ord: "<bid_ntce_ord>"` 로 넣는다(숫자 `no` 는 표 번호라 이름이 겹치므로 `no_`). `Sheet` 시그니처를 `export function Sheet({ loggedIn, reviewed }: { loggedIn: boolean; reviewed: string[] })` 로 바꾸고, 1행의 `SheetExpand actions` 안 `<Btn variant="review">검토</Btn>` 를

```tsx
<ReviewButton no={r.no_} ord={r.ord} via="1248177731" why={r.why} reviewed={reviewed.includes(`${r.no_}-${r.ord}`)} loggedIn={loggedIn} />
```

로 바꾼다(`import { ReviewButton } from "@/components/ReviewButton";`). `SheetRow` 의 `reviewed` prop 은 `r.reviewed || reviewed.includes(...)` 로.

- [x] **Step 4: 확인** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0. 개발 서버(`npm run dev -- --port 3000`, 3000 이 잡혀 있으면 3001)에서 `/dev/foundation` 을 열어 비로그인이면 ☆ 버튼이 `/login?next=%2Fdev%2Ffoundation` 링크, 검토 버튼도 같은 링크인지 본다. (로그인 뒤 동작은 Task 6 스크립트가 검사한다.)

- [x] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/StarCompany.tsx frontend/src/components/ReviewButton.tsx "frontend/src/app/(renewal)/dev/foundation" && git commit -m "feat(renewal): StarCompany(☆ 회사 저장)·ReviewButton(검토) — 브라우저 RLS 직접 쓰기, 비로그인은 로그인 링크, /dev/foundation 에 실제 연결"
```

---

### Task 5: `/saved` — 비로그인 판 · 두 탭 · 공고 표 · 회사 표

**Files:**
- Create: `frontend/src/app/(renewal)/saved/page.tsx`, `SavedTabs.tsx`, `NoticeRows.tsx`, `CompanyRows.tsx`

- [x] **Step 1: `SavedTabs`** (클라이언트 — 탭 상태만. 시안대로 URL·해시 반영 없음)

```tsx
// frontend/src/app/(renewal)/saved/SavedTabs.tsx
"use client";

import { useState, type ReactNode } from "react";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "n", label: "공고" },
  { id: "c", label: "저장한 회사" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function SavedTabs({ counts, notices, companies }: { counts: Record<TabId, number>; notices: ReactNode; companies: ReactNode }) {
  const [tab, setTab] = useState<TabId>("n");
  return (
    <>
      <PageHead title="검토함" className="pb-0">
        <div role="tablist" aria-label="검토함" className="flex gap-6 text-[15px] max-sm:gap-[18px] max-sm:text-[14px]">
          {TABS.map((t) => {
            const on = tab === t.id;
            return (
              <button key={t.id} type="button" role="tab" id={`tab-${t.id}`} aria-selected={on} aria-controls={`pane-${t.id}`} onClick={() => setTab(t.id)}
                className={cn("-mb-px cursor-pointer border-b-2 border-transparent pb-3 text-ink-g", on && "border-ink font-[650] text-ink")}>
                {t.label}
                <small className="ml-1.5 text-[13.5px] font-[450] text-ink-mute">{counts[t.id]}</small>
              </button>
            );
          })}
        </div>
      </PageHead>
      <Panel className="mt-[22px] pt-1.5">
        <div role="tabpanel" id="pane-n" aria-labelledby="tab-n" hidden={tab !== "n"}>{notices}</div>
        <div role="tabpanel" id="pane-c" aria-labelledby="tab-c" hidden={tab !== "c"}>{companies}</div>
      </Panel>
    </>
  );
}
```

`PageHead` 의 `children` 이 먹 괘선 바로 위에 놓이는 자리다(01). 탭 밑줄 2px 가 그 괘선 위에 앉도록 `-mb-px` 를 쓴다 — `PageHead` 가 children 아래에 padding 을 두면 `className="pb-0"` 이 그것을 지운다는 전제이니, 01 의 `PageHead` 구현에서 children 래퍼의 padding 클래스를 확인해 같은 효과가 나게 맞춘다(렌더 결과: 선택 탭의 먹 밑줄이 머리 괘선과 겹쳐 보여야 한다. 시안 `.tabs2 a { margin-bottom:-1px }`).

- [x] **Step 2: `NoticeRows`** (클라이언트 — 해제/되돌리기)

```tsx
// frontend/src/app/(renewal)/saved/NoticeRows.tsx
// 검토함 공고 표. 격자는 시안 gen_saved.py:34 (제목 / 마감 84 / 추정가 84 / 해제 64), 390 은 제목 / 마감 72 만.
// 해제는 행이 흐려지고 "되돌리기"로 바뀐다 — 즉시 사라지지 않는다(시안). 되돌리기는 같은 값으로 다시 insert.
"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReviewedNoticeRow } from "@/lib/saved";
import { won } from "@/lib/format";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[minmax(0,1fr)_84px_84px_64px] gap-x-3 items-start max-sm:grid-cols-[minmax(0,1fr)_72px]";

function Row({ r, past }: { r: ReviewedNoticeRow; past: boolean }) {
  const router = useRouter();
  const [removed, setRemoved] = useState(false);
  async function toggle() {
    const sb = getBrowserSupabase();
    const next = !removed;
    setRemoved(next);
    const { error } = next
      ? await sb.from("reviewed_notices").delete().eq("bid_ntce_no", r.no).eq("bid_ntce_ord", r.ord)
      : await sb.from("reviewed_notices").insert({ bid_ntce_no: r.no, bid_ntce_ord: r.ord, via_bizrno_norm: r.via?.bizrnoNorm ?? null, why: r.why });
    if (error && error.code !== "23505") { setRemoved(!next); return; }
    router.refresh();
  }
  const hot = !past && !!r.d && r.d.days <= 7;
  return (
    <div data-saved-row className={cn(GRID, "border-b border-rule py-3 transition-opacity duration-300", removed && "opacity-35", past && "text-ink-mute")}>
      <span className="min-w-0">
        <span className={cn("block text-[16px] font-semibold leading-snug", past ? "text-ink-mute" : "text-ink")}>
          <Link href={`/notices/${r.no}`} className="hover:border-b hover:border-orange">{r.title}</Link>
        </span>
        <span className="mt-1 block text-[13.5px] text-ink-dim max-sm:text-[13px]">
          {r.via && (
            <span className={cn("before:mr-1 before:text-[11px] before:content-['★']", past ? "before:text-[#b8b6b0]" : "before:text-orange")}>{r.via.name}</span>
          )}
          {r.via && <span className="mx-[7px] text-[#c9c9c4]">·</span>}
          <span>{r.org}</span>
          {r.why && !past && <span className="ml-[7px] rounded-[4px] border border-hair px-1.5 py-px text-[12px] text-ink-g">{r.why}</span>}
        </span>
      </span>
      <span className={cn("num pt-0.5 text-right text-[15px] font-semibold", hot && "text-orange", past && "font-medium")}>
        {r.d ? (r.d.days < 0 ? "마감" : `D-${r.d.days}`) : "—"}
        {r.d && <small className={cn("block text-[12px] font-normal", past ? "text-[#9b9a95]" : "text-ink-mute")}>{r.d.month}.{String(r.d.day).padStart(2, "0")}</small>}
      </span>
      <span className="num pt-0.5 text-right text-[15px] max-sm:hidden">{won(r.price)}</span>
      <span className="pt-1 text-right text-[13px] max-sm:hidden">
        <button type="button" onClick={toggle} data-unreview className={cn("cursor-pointer border-b", removed ? "border-ink text-ink" : "border-[#d8d6d0] text-ink-g hover:border-orange")}>
          {removed ? "되돌리기" : "해제"}
        </button>
      </span>
    </div>
  );
}

export function NoticeRows({ live, past }: { live: ReviewedNoticeRow[]; past: ReviewedNoticeRow[] }) {
  if (live.length === 0 && past.length === 0) {
    return (
      <div data-saved-empty className="pb-2.5 pt-[30px] text-[14px] leading-[1.7] text-ink-g">
        <b className="mb-1 block text-[16px] font-[650] text-ink">검토 표시한 공고가 없습니다</b>
        결과 표의 행을 펼쳐 검토를 누르면 여기에 보관됩니다.
      </div>
    );
  }
  return (
    <>
      <div className={cn(GRID, "border-b border-ink pb-2 pt-4 text-[12px] text-ink-mute max-sm:hidden")}>
        <span>공고 · 결과를 본 회사 · 발주기관 · 근거</span><span className="text-right">마감</span><span className="text-right">추정가</span><span />
      </div>
      {live.map((r) => <Row key={`${r.no}-${r.ord}`} r={r} past={false} />)}
      {past.length > 0 && (
        <div data-saved-past className="mt-[22px]">
          <span className="block border-b border-hair pb-2 text-[12px] text-ink-mute">마감 지남 {past.length}건 — 마감 30일 뒤 자동 정리</span>
          {past.map((r) => <Row key={`${r.no}-${r.ord}`} r={r} past />)}
        </div>
      )}
    </>
  );
}
```

- [x] **Step 3: `CompanyRows`** (클라이언트 — ★ 해제/되돌리기)

```tsx
// frontend/src/app/(renewal)/saved/CompanyRows.tsx
// 검토함 저장한 회사 표. 격자 시안 gen_saved.py:46 (회사 / 오늘 150 / 마감 110 / 결과·해제 110), 390 은 회사 / 오늘 만.
// "오늘 N건 검토할 공고"는 추천 캐시 기준 — 캐시가 없으면 "—"와 "결과" 링크만.
"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { SavedCompanyRow } from "@/lib/saved";
import { rgnBase } from "@/lib/format";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[minmax(0,1fr)_150px_110px_110px] gap-x-3 items-start max-sm:grid-cols-[minmax(0,1fr)_auto]";

function Row({ c }: { c: SavedCompanyRow }) {
  const router = useRouter();
  const [removed, setRemoved] = useState(false);
  async function toggle() {
    const sb = getBrowserSupabase();
    const next = !removed;
    setRemoved(next);
    const { error } = next
      ? await sb.from("saved_companies").delete().eq("bizrno_norm", c.bizrnoNorm)
      : await sb.from("saved_companies").insert({ bizrno_norm: c.bizrnoNorm });
    if (error && error.code !== "23505") { setRemoved(!next); return; }
    router.refresh();
  }
  const s = c.stats;
  const hot = !!s?.soonest && s.soonest.days <= 7;
  return (
    <div data-saved-company className={cn(GRID, "border-b border-rule py-3.5 transition-opacity duration-300", removed && "opacity-35")}>
      <span className="min-w-0">
        <span className="block text-[16px] font-semibold text-ink before:mr-1.5 before:text-[13px] before:text-orange before:content-['★']">{c.name}</span>
        <span className="mt-1 block text-[13.5px] text-ink-dim">
          <span>{rgnBase(c.region) || "—"}</span><span className="mx-[7px] text-[#c9c9c4]">·</span><span>등록업종 {c.industries}</span>
        </span>
      </span>
      <span className="num pt-0.5 text-[14px] text-ink-dim">
        {s ? <><b className="text-[15px] font-semibold text-ink max-sm:text-[16px]">{s.total}건</b> 검토할 공고</> : <span className="text-ink-mute">— 결과 없음</span>}
        {s && <small className="block text-[12px] text-ink-mute">이번 주 마감 {s.week}건</small>}
      </span>
      <span className="num pt-0.5 text-[14px] max-sm:hidden">
        {s?.soonest ? (
          <><span className={cn("text-[15px] font-semibold", hot ? "text-orange" : "text-ink")}>D-{s.soonest.days}</span>
            <small className="block text-[12px] text-ink-mute">가장 빠른 마감 {s.soonest.month}.{String(s.soonest.day).padStart(2, "0")}</small></>
        ) : <span className="text-ink-mute">—</span>}
      </span>
      <span className="flex items-center justify-end gap-3 pt-0.5 text-[13px] max-sm:hidden">
        <Link href={`/companies/${c.bizrnoNorm}`} className="border-b border-[#e3e1dc] text-ink hover:border-orange">결과</Link>
        <button type="button" onClick={toggle} data-unstar className={cn("cursor-pointer border-b", removed ? "border-ink text-ink" : "border-[#d8d6d0] text-ink-g hover:border-orange")}>
          {removed ? "되돌리기" : "★ 해제"}
        </button>
      </span>
    </div>
  );
}

export function CompanyRows({ rows }: { rows: SavedCompanyRow[] }) {
  if (rows.length === 0) {
    return (
      <div data-saved-empty className="pb-2.5 pt-[30px] text-[14px] leading-[1.7] text-ink-g">
        <b className="mb-1 block text-[16px] font-[650] text-ink">저장한 회사가 없습니다</b>
        회사 페이지 또는 결과 머리의 ☆ 로 저장합니다.
      </div>
    );
  }
  return (
    <>
      <div className={cn(GRID, "border-b border-ink pb-2 pt-4 text-[12px] text-ink-mute max-sm:hidden")}>
        <span>회사</span><span>오늘</span><span>마감</span><span />
      </div>
      {rows.map((c) => <Row key={c.bizrnoNorm} c={c} />)}
    </>
  );
}
```

- [x] **Step 4: `page.tsx`**

```tsx
// frontend/src/app/(renewal)/saved/page.tsx
// 검토함 — 로그인 사용자 전용. 비로그인은 리다이렉트가 아니라 안내 판(마스터 §3.2). 세션 쿠키를 읽으므로 항상 동적.
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { getSessionUser } from "@/lib/auth";
import { getReviewedNotices, getSavedCompanies } from "@/lib/saved";
import { CompanyRows } from "./CompanyRows";
import { NoticeRows } from "./NoticeRows";
import { SavedTabs } from "./SavedTabs";

export const metadata: Metadata = { title: "검토함 | 조달핏", robots: { index: false, follow: false } };

export default async function SavedPage() {
  const user = await getSessionUser();
  if (!user) {
    return (
      <>
        <PageHead title="검토함" />
        <Panel className="mt-[22px]">
          <div data-saved-gate className="flex flex-wrap items-center gap-3.5 pb-2.5 pt-[26px] text-[14.5px]">
            <div>
              <b className="font-semibold text-ink">검토함은 로그인 후 사용</b>
              <span className="mt-1 block text-[13.5px] text-ink-dim">검토 표시한 공고와 저장한 회사를 보관</span>
            </div>
            <span className="grow" />
            <span className="flex gap-2">
              <Btn href="/login?next=%2Fsaved">로그인</Btn>
              <Btn variant="dark" href="/signup?next=%2Fsaved">회원가입</Btn>
            </span>
          </div>
        </Panel>
      </>
    );
  }
  const today = new Date();
  const [{ live, past }, companies] = await Promise.all([getReviewedNotices(today), getSavedCompanies(today)]);
  return (
    <SavedTabs
      counts={{ n: live.length, c: companies.length }}
      notices={<NoticeRows live={live} past={past} />}
      companies={<CompanyRows rows={companies} />}
    />
  );
}
```

- [x] **Step 5: 확인** — `npx tsc --noEmit -p tsconfig.json; echo $?` → 0, `npm run lint` 통과. 개발 서버에서 비로그인 `/saved` 가 안내 판 + 버튼 둘(로그인 → `/login?next=%2Fsaved`)로 뜨는지, 탭이 없는지 본다.

- [x] **Step 6: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add "frontend/src/app/(renewal)/saved" && git commit -m "feat(renewal): /saved 검토함 — 비로그인 안내 판, 공고(마감 순·마감 지남 묶음·해제/되돌리기)·저장한 회사(오늘·마감·★ 해제) 두 탭"
```

---

### Task 6: 화면 검증 `check_saved.py`

**Files:**
- Create: `frontend/scripts/check_saved.py`

비로그인 검사는 항상 돈다. 로그인 검사는 `frontend/.env.local` 의 `NEXT_PUBLIC_SUPABASE_URL`·`NEXT_PUBLIC_SUPABASE_ANON_KEY` 와 `backend/.env` 의 `SUPABASE_SERVICE_ROLE_KEY` 가 있고 0054 가 적용돼 있을 때만 돈다(없으면 "로그인 검사 건너뜀" 을 찍고 0 으로 끝난다 — 02 Task 2 가 끝나기 전에도 스크립트는 통과해야 한다). 테스트 사용자는 Admin API 로 만들고(`email_confirm: true`, 확인 메일 없이), 끝나면 지운다(cascade 로 저장 행도 사라진다).

- [x] **Step 1: 스크립트**

```python
# frontend/scripts/check_saved.py
"""검토함(03) 화면 검증 — 시안 gen_saved.py --check 를 옮긴 것.

사용: cd backend && uv run --no-sync python ../frontend/scripts/check_saved.py
주소: SAVED_BASE (기본 http://localhost:3000). 3000 이 다른 프로젝트면 SAVED_BASE=http://localhost:3001.

비로그인: /saved 안내 판(버튼 2, 탭 0), 금지어 0, 주황 면 0, 인주 0, 바닥색, 390 가로 넘침 없음.
로그인(키 있을 때만): Admin API 로 사용자 생성 → /login 폼 → /dev/foundation 에서 ☆·검토 → /saved 공고 1(★ 칩·근거)·회사 1(★)
→ 해제 → 흐림+되돌리기 → 되돌리기 → 390 에서 추정가·해제 열 숨김 → 사용자 삭제.
"""
import json, os, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("SAVED_BASE", "http://localhost:3000")
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
BANNED = ["이메일 구독", "맞아요", "예요", "에요", "해드려요", "하세요", "검토 인장", "낼 수 있", "메모", "폴더", "매직링크", "회사 연결", "주십시오"]

def env(path, key):
    m = re.search(rf"^{key}=(.*)$", Path(path).read_text(encoding="utf-8"), re.M) if Path(path).exists() else None
    return m.group(1).strip().strip('"') if m else None

RULES = """() => { const cs = e => getComputedStyle(e);
  const all = [...document.querySelectorAll('body *')];
  return { bg: cs(document.querySelector('.rn')).backgroundColor,
    orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length,
    injuk: all.some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); }),
    overflow: document.documentElement.scrollWidth > window.innerWidth } }"""

def rules(pg):
    txt = pg.evaluate("document.body.innerText")
    bad = [w for w in BANNED if w in txt]
    assert not bad, f"금지어 {bad} @ {pg.url}"
    s = pg.evaluate(RULES)
    assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"] and not s["overflow"], (pg.url, s)

def goto(pg, path):
    pg.goto(BASE + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(400)

def admin(url, key, method, path, body=None):
    req = urllib.request.Request(f"{url}/auth/v1{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    url = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_URL")
    anon = env(ROOT / "frontend/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    srv = env(ROOT / "backend/.env", "SUPABASE_SERVICE_ROLE_KEY")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900})

        # ── 비로그인
        goto(pg, "/saved"); rules(pg)
        g = pg.evaluate("""() => ({ btns: document.querySelectorAll('[data-saved-gate] a[href^="/login?next="], [data-saved-gate] a[href^="/signup?next="]').length,
            tabs: document.querySelectorAll('[role=tab]').length, h1: document.querySelector('h1').textContent })""")
        assert g["btns"] == 2 and g["tabs"] == 0 and g["h1"] == "검토함", g
        pg.screenshot(path=str(OUT / "_shot_saved_guest.png"))
        goto(pg, "/dev/foundation")
        assert pg.evaluate("!!document.querySelector('[data-star=guest][href^=\"/login?next=\"]') && !!document.querySelector('[data-review=guest][href^=\"/login?next=\"]')")
        pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/saved"); rules(pg)
        pg.set_viewport_size({"width": 1280, "height": 900})

        if not (url and anon and srv):
            print("ok saved(guest): gate 2 buttons · tabs 0 · foundation guest links · 390 — 로그인 검사 건너뜀(키 없음)")
            return 0

        # ── 로그인
        email, pw_ = "check-saved@jodalfit.test", "check-saved-pw-1"
        for u in admin(url, srv, "GET", "/admin/users?per_page=200").get("users", []):
            if u.get("email") == email: admin(url, srv, "DELETE", f"/admin/users/{u['id']}")
        user = admin(url, srv, "POST", "/admin/users", {"email": email, "password": pw_, "email_confirm": True})
        try:
            goto(pg, "/login?next=%2Fdev%2Ffoundation")
            pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw_); pg.click("button[type=submit]")
            pg.wait_for_url(re.compile(r"/dev/foundation")); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
            pg.click("[data-star=off]"); pg.wait_for_selector("[data-star=on]"); pg.wait_for_timeout(800)
            pg.locator("button.num[aria-expanded]").first.click() if pg.evaluate("document.querySelectorAll('.x-wrap[data-open=true]').length") == 0 else None
            pg.click("[data-review=off]"); pg.wait_for_selector("[data-review=on]"); pg.wait_for_timeout(800)
            assert pg.evaluate("document.querySelectorAll('nav [data-menu] a[href^=\"/companies/1248177731\"]').length") >= 0  # 메뉴는 닫혀 있어도 DOM 에 없을 수 있음

            goto(pg, "/saved"); rules(pg)
            s = pg.evaluate("""() => ({ tabs: [...document.querySelectorAll('[role=tab] small')].map(e => e.textContent),
                rows: document.querySelectorAll('#pane-n [data-saved-row]').length,
                star: getComputedStyle(document.querySelector('#pane-n [data-saved-row] span span span'), '::before').color,
                why: !!document.querySelector('#pane-n [data-saved-row] .rounded-\\\\[4px\\\\]') })""")
            assert s["tabs"] == ["1", "1"] and s["rows"] == 1 and s["star"] == "rgb(249, 115, 22)", s
            pg.screenshot(path=str(OUT / "_shot_saved_notices.png"), full_page=True)
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            u = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); return { op: getComputedStyle(r).opacity, t: r.querySelector('[data-unreview]').textContent } }""")
            assert float(u["op"]) < 0.5 and u["t"] == "되돌리기", u
            pg.click("[data-unreview]"); pg.wait_for_timeout(300)
            assert pg.evaluate("document.querySelector('#pane-n [data-unreview]').textContent") == "해제"

            pg.click("#tab-c"); pg.wait_for_timeout(200)
            c = pg.evaluate("""() => ({ shown: !document.getElementById('pane-c').hidden, rows: document.querySelectorAll('#pane-c [data-saved-company]').length,
                name: document.querySelector('#pane-c [data-saved-company] span span').textContent, result: !!document.querySelector('#pane-c a[href="/companies/1248177731"]') })""")
            assert c["shown"] and c["rows"] == 1 and "한종산업개발" in c["name"] and c["result"], c
            pg.screenshot(path=str(OUT / "_shot_saved_companies.png"), full_page=True)

            pg.set_viewport_size({"width": 390, "height": 844}); goto(pg, "/saved"); rules(pg)
            m = pg.evaluate("""() => { const r = document.querySelector('#pane-n [data-saved-row]'); const ch = r.children;
                return { price: getComputedStyle(ch[2]).display, un: getComputedStyle(ch[3]).display } }""")
            assert m["price"] == "none" and m["un"] == "none", m
            pg.screenshot(path=str(OUT / "_shot_saved_390.png"), full_page=True)

            # 메뉴 ★ 목록·검토 건수 (Nav)
            pg.set_viewport_size({"width": 1280, "height": 900}); goto(pg, "/saved")
            pg.click("nav button[aria-controls=nav-user-menu], nav button[aria-expanded]"); pg.wait_for_timeout(200)
            n = pg.evaluate("""() => ({ star: document.querySelectorAll('[data-menu] a[href^="/companies/1248177731"]').length,
                cnt: [...document.querySelectorAll('[data-menu] small')].map(e => e.textContent).find(t => t.includes('검토한 공고')) })""")
            assert n["star"] == 1 and n["cnt"] == "검토한 공고 1건", n
        finally:
            admin(url, srv, "DELETE", f"/admin/users/{user['id']}")
        print("ok saved: guest gate · login · ☆ · 검토 · notices 1(★·why) · 해제/되돌리기 · companies 1 · nav ★ 1/검토 1건 · 390 cols hidden · banned 0")
        return 0

if __name__ == "__main__":
    sys.exit(main())
```

Nav 트리거 버튼의 선택자(`nav button[aria-controls=nav-user-menu]`)는 `Nav.tsx:58-61` 의 실제 속성으로 맞춘다 — 트리거에 `aria-controls="nav-user-menu"` 가 없으면 Nav 에 그 속성을 추가한다(접근성상도 맞다). `/login` 폼의 입력 선택자는 `LoginForm.tsx` 의 실제 `type`·`name` 으로 맞춘다.

- [x] **Step 2: 실행** — 개발 서버를 띄운 채 `cd C:/Dev/personal/jodalfit/backend && uv run --no-sync python ../frontend/scripts/check_saved.py` → 키가 없으면 `ok saved(guest): …`, 있으면 `ok saved: …`. 실패하면 원인을 고치고 다시 돈다(단정값을 맞추려고 스크립트를 느슨하게 하지 않는다).

- [x] **Step 3: lint · build** — `cd C:/Dev/personal/jodalfit/frontend && npm run lint && npm run build 2>&1 | tail -3` → 성공(`/saved` 가 `ƒ` 동적으로 잡힌다).

- [x] **Step 4: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/scripts/check_saved.py frontend/scripts/_shot_saved_*.png frontend/src/components/Nav.tsx && git commit -m "test(renewal): 검토함 Playwright 검증 — 비로그인 판, (키 있으면) 가입·로그인·☆·검토·해제·390·Nav ★"
```

---

### Task 7: 기록 · 푸시

**Files:**
- Modify: `docs/design/README.md` (끝에 절 추가), `docs/superpowers/plans/2026-10-23-renewal-03-saved.md` (체크박스)

- [x] **Step 1: README 기록** — `docs/design/README.md` 맨 끝에 추가:

```markdown
## 구현 — 03 saved (2026-10-23, 브랜치 `renewal`)
0054 `saved_companies`·`reviewed_notices`(RLS, `user_id default auth.uid()`, 마감 30일 지난 검토 행 pg_cron 주 1회 삭제). 쓰기는 브라우저 Supabase 클라이언트가 RLS 테이블에 직접(라우트 핸들러 없음), 읽기는 `lib/saved.ts`(세션 클라이언트 + service_role 공개 조인). 회사 행의 "오늘 N건·이번 주 마감·가장 빠른 마감"은 `company_recommendations` 캐시에서 마감 지난 항목을 걷어내고 센다 — 캐시 없으면 `—`(백엔드 호출 없음). 부품 `StarCompany`(☆ 회사 저장 / ★ 저장됨)·`ReviewButton`(검토 / 검토함), 둘 다 비로그인이면 `/login?next=` 링크. `/saved` 는 탭 둘(공고: 마감 순 + 마감 지남 회색 묶음 / 저장한 회사), 해제는 흐림 + 되돌리기. Nav 메뉴 ★ 목록·검토 건수는 실제 값. `/dev/foundation` 의 ☆·검토가 실제 부품이라 검증 스크립트가 거기서 저장을 돌린다.
검증: `scripts/check_saved.py`(비로그인은 항상, 로그인 흐름은 공개 키 + 0054 적용 뒤). `lib/saved-stats.test.ts` 4건.
남은 것: 결과·회사·공고 페이지에 부품 꽂기는 05·06·07. 마감 지난 공고의 "낙찰 · 2위" 칸(README 시안 메모)은 넣지 않았다.
```

- [x] **Step 2: 계획 체크박스** — 이 문서의 끝난 Step 을 `- [x]` 로.

- [x] **Step 3: 커밋 · 푸시**

```bash
cd C:/Dev/personal/jodalfit && git add docs/design/README.md docs/superpowers/plans/2026-10-23-renewal-03-saved.md && git commit -m "docs(design): 구현 03 saved 기록" && git push origin renewal
```

---

## 자체 검토

- **시안 ↔ 태스크**: 탭·격자·마감 표기·해제/되돌리기·마감 지남 묶음·빈 상태 둘·비로그인 판 → Task 5. ★ 칩·근거 칩(검토 시점 저장) → Task 1(`why`)·4·5. 회사 행 숫자 → Task 2·3. Nav ★ 목록·검토 건수 → Task 3. 390(추정가·해제 열 숨김, 회사 탭 마감·결과 열 숨김, 한 단) → Task 5 GRID + Task 6.
- **마스터 조항**: §3.3 테이블·정책·pg_cron(Task 1), 사용자 테이블은 anon+세션(Task 3·4·5), service_role 은 공개 데이터만(Task 3). §3.2 `/saved` 비로그인은 안내 판(Task 5). §3.5 금지어·`rgnBase`·주황은 선(★ 글자·밑줄·D-7 만). §3.6 Playwright + `node --test`.
- **타입 일관**: `DLeft`·`CompanyStats`(saved-stats) ↔ `SavedCompanyRow.stats`·`ReviewedNoticeRow.d`(saved) ↔ `NoticeRows`/`CompanyRows` props. `StarCompany(bizrnoNorm, saved, loggedIn)`·`ReviewButton(no, ord, via, why, reviewed, loggedIn)` 는 Task 4 정의 그대로 `/dev/foundation` 에서 호출. `getNavSaved` 반환형 = `NavUser` 의 `savedCompanies`·`reviewedCount`.
- **05·06·07 이 이어받는 접점**: `StarCompany` 를 PageHead `aside` 에, `ReviewButton` 을 `SheetExpand actions` 에(`why={strongestWhy(bid.score_breakdown)}`, `via={bizrnoNorm}`), 초기값은 `getSavedCompanyKeys`·`getReviewedKeys`. `/settings` 는 여전히 없음(09).
- **빠진 것(의도)**: 낙찰 여부 칸, 메모·폴더·정렬 옵션(시안이 없음), 되돌리기 이후 재정렬(새로고침 때 정렬됨).
