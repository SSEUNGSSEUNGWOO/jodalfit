# 리뉴얼 01 — foundation: 토큰 · 셸 · 공용 부품 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 마스터: `2026-10-19-renewal-00-master.md` §3 공통 결정을 먼저 읽는다.

**Goal:** 시안 7개가 공유하는 문법(바닥 + 흰 판, 먹 괘선 하나, 주황은 선, 글자 단계, 공문 톤)을 Tailwind v4 토큰과 공용 컴포넌트(Logo · Nav · SiteFooter · PageHead · Panel · Sheet · Gate · Btn)로 만들고, 그것만 모아 놓은 확인용 페이지 `/dev/foundation` 을 Playwright 로 검증한다. 뒤 계획 02~09 는 이 부품만 쓴다.

**Architecture:** 새 토큰은 `globals.css` 의 `@theme` 에 **추가**한다(옛 `gc-*` 토큰·`world-gc` 유틸은 09 컷오버에서 지운다 — 지금 지우면 옛 페이지가 깨진다). 새 컴포넌트는 `src/components/` 평평한 폴더에 새 이름으로 두고(`Header.tsx`·`Footer.tsx`·`Brand.tsx` 는 그대로), 값은 시안 생성기의 CSS 에서 그대로 옮긴다. 동작 검증은 테스트 프레임워크 없이 `node --test`(순수 함수) + Playwright 스크립트(화면)로 한다.

**Tech Stack:** Next.js 16.2 App Router · React 19 · Tailwind v4 `@theme` · TypeScript · Node 24(`node --test` 가 .ts 를 그대로 실행) · Playwright(backend `.venv`, `chrome-headless-shell`) · 브랜치 `renewal`.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `frontend/src/app/globals.css` | 새 토큰 `@theme` 블록 추가(`--color-paper` … `--color-orange`, `--ease-sheet`), 공용 유틸 클래스 `.t-k` `.rule-ink` `.hairline` `.num` |
| `frontend/src/components/Logo.tsx` | `Mark`(currentColor, 64 격자) · `Mark16`(16 정수 격자) · `Tile`(주황 타일 + 흰 마크) · `Lockup`(타일 22 + 조달핏) — `docs/design/brand/*.svg` 를 그대로 |
| `frontend/src/components/Nav.tsx` | 상단 nav. 링크(추천·검토함·개선 기록) + 오른쪽 `로그인` 또는 로그인된 이메일 메뉴(저장한 회사·검토함·설정·로그아웃). 세션은 prop 으로 받는다(02 가 공급) |
| `frontend/src/components/SiteFooter.tsx` | 바닥: 출처·갱신, 개인정보·약관·비공개 요청, 문의 |
| `frontend/src/components/PageHead.tsx` | 머리: 제목(32) + 제목 옆 작은 글 + 메타 줄(· 구분) + 아래 먹 괘선. 슬롯 `aside`(다른 회사·☆ 자리), `children`(걸러낸 경로 등) |
| `frontend/src/components/Panel.tsx` | 흰 판(14px, 헤어라인, 390 은 12px). `PanelHead`(제목 16 + 요약, 아래 먹 괘선) |
| `frontend/src/components/Sheet.tsx` | 표: `SheetHead`(열 머리) · `SheetRow`(번호·제목·둘째 줄·마감·추정가, 클릭 펼침) · `SheetExpand`(참가 자격 / 추천 근거 / 버튼) · `SheetFade`(흐림 묶음). 결과·회사·검토함이 쓴다 |
| `frontend/src/components/Gate.tsx` | 표 안 게이트 한 줄: "나머지 N건은 로그인 후 공개" + 로그인 / 회원가입 두 버튼(링크는 `/login?next=` `/signup?next=`) |
| `frontend/src/components/Btn.tsx` | 버튼·링크 공용(`<a>` 또는 `<button>`): `dark` · `line` · `review`(주황 헤어라인) · `text`. shadcn `Button` 은 asChild 가 없어 링크에 못 쓴다 |
| `frontend/src/lib/format.ts` | `won`(50.3억·200만·—) · `wonFull`(6,824,573,000원) · `dLeft`(마감까지 일수·날짜) · `ymd`(2026.10.16) · `rgnBase`(기초자치단체까지) |
| `frontend/src/lib/format.test.ts` | 위 함수 `node --test` |
| `frontend/src/app/dev/foundation/page.tsx` | 부품 전시 페이지(noindex). 09 에서 삭제 |
| `frontend/scripts/check_foundation.py` | Playwright 검증(금지어·인주·주황 면·요소·390) + 캡처 `frontend/scripts/_shot_foundation*.png` |
| `frontend/.gitignore` | `scripts/_shot_*.png` 무시 |

---

### Task 0: 브랜치

**Files:** 없음

- [ ] **Step 1: `renewal` 브랜치 만들기**

```bash
cd C:/Dev/personal/jodalfit
git checkout -b renewal
git push -u origin renewal
```
Expected: `Switched to a new branch 'renewal'`

---

### Task 1: 포맷 유틸 + 테스트

**Files:**
- Create: `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/format.test.ts`

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
// frontend/src/lib/format.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { won, wonFull, dLeft, ymd, rgnBase } from "./format.ts";

test("won — 억·만 축약, 없으면 —", () => {
  assert.equal(won(5025454546), "50.3억");
  assert.equal(won(6000000000), "60억");       // .0억 은 억
  assert.equal(won(2000000), "200만");
  assert.equal(won(0), "—");
  assert.equal(won(null), "—");
});

test("wonFull — 전액 원", () => {
  assert.equal(wonFull(6824573000), "6,824,573,000원");
  assert.equal(wonFull(null), "—");
});

test("dLeft — 오늘 기준 남은 일수와 날짜", () => {
  const today = new Date(2026, 9, 16);         // 2026-10-16
  assert.deepEqual(dLeft("2026-10-29", today), { days: 13, month: 10, day: 29 });
  assert.deepEqual(dLeft("2026-10-16T00:00:00+00:00", today), { days: 0, month: 10, day: 16 });
});

test("ymd — 2026.10.16", () => {
  assert.equal(ymd("2026-10-16"), "2026.10.16");
  assert.equal(ymd("2026-10-16T02:19:35+00:00"), "2026.10.16");
  assert.equal(ymd(null), "—");
});

test("rgnBase — 기초자치단체까지, 일반구·동 제거", () => {
  assert.equal(rgnBase("경상남도 창원시 마산합포구"), "경상남도 창원시");
  assert.equal(rgnBase("부산광역시 동구"), "부산광역시 동구");
  assert.equal(rgnBase("경기도 성남시 분당구 정자동"), "경기도 성남시");
  assert.equal(rgnBase(null), "");
});
```

- [ ] **Step 2: 실패 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && node --test src/lib/format.test.ts
```
Expected: `Cannot find module './format.ts'` 로 FAIL

- [ ] **Step 3: 구현**

```ts
// frontend/src/lib/format.ts
/** 시안 생성기 gen_results.py::won/dleft, gen_company.py::ymd, gen_split.py::rgn_base 와 같은 규칙. */

export function won(v: number | string | null | undefined): string {
  const n = typeof v === "string" ? Number(v) : v;
  if (!n) return "—";
  if (n >= 100_000_000) {
    const s = (n / 100_000_000).toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `${s.replace(/\.0$/, "")}억`;
  }
  return `${Math.floor(n / 10_000).toLocaleString("ko-KR")}만`;
}

export function wonFull(v: number | string | null | undefined): string {
  const n = typeof v === "string" ? Number(v) : v;
  if (!n) return "—";
  return `${Math.trunc(n).toLocaleString("ko-KR")}원`;
}

/** 마감까지 남은 일수. 날짜 문자열 앞 10자리만 쓴다(시간대 무시 — 나라장터 마감은 날짜 단위로 본다). */
export function dLeft(dateStr: string, today: Date = new Date()): { days: number; month: number; day: number } {
  const [y, m, d] = dateStr.slice(0, 10).split("-").map(Number);
  const target = new Date(y, m - 1, d);
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((target.getTime() - base.getTime()) / 86_400_000);
  return { days, month: m, day: d };
}

export function ymd(s: string | null | undefined): string {
  if (!s) return "—";
  return `${s.slice(0, 4)}.${s.slice(5, 7)}.${s.slice(8, 10)}`;
}

/** 표시용 지역 — 시·도 + 시·군·구까지. 일반구(마산합포구·분당구)·동은 지역 제한 단위가 아니다. */
export function rgnBase(rgn: string | null | undefined): string {
  return (rgn ?? "").split(/\s+/).filter(Boolean).slice(0, 2).join(" ");
}
```

- [ ] **Step 4: 통과 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && node --test src/lib/format.test.ts
```
Expected: `# pass 5` `# fail 0`

- [ ] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/lib/format.ts frontend/src/lib/format.test.ts && git commit -m "feat(renewal): 포맷 유틸 won·wonFull·dLeft·ymd·rgnBase + node --test"
```

---

### Task 2: 토큰과 공용 유틸 클래스

**Files:**
- Modify: `frontend/src/app/globals.css` — `@theme { … }` 블록 끝(`--shadow-xl` 줄 뒤)과 파일 끝

- [ ] **Step 1: `@theme` 에 새 토큰 추가** — `--shadow-xl: …;` 줄 바로 아래에 붙인다

> 품질 검토 기록(2026-10-19): 컴파일된 CSS 에서 덮어쓰기 확인됨. 컷오버 전까지 옛 `Footer` 등은 먹 제목 + 네이비 본문이 섞여 보인다 — 의도된 과도기, 중간에 '고치지' 말 것. `.rn :focus-visible` 과 `.world-gc :focus-visible` 은 특이도가 같으니 두 범위를 중첩하지 않는다.

> 주의: `--color-ink` 와 `--color-line` 은 옛 `@theme` 에 이미 있다(#17233a · #dde3ec). 같은 이름을 **아래에서 다시 선언해 덮어쓴다** — 옛 페이지의 `text-ink` 가 먹 #141414 로, `border-line` 이 #d8d6d0 로 바뀐다. 의도한 것이다(컷오버 때 전 페이지가 먹으로 간다). 옛 `--color-ink-2…7` 은 건드리지 않는다.

```css
  /* ── 2026-10 리뉴얼 토큰 (docs/design/README.md · renewal-00-master §3.1). 옛 gc-* 는 09 컷오버에서 삭제 ── */
  --color-paper:   #faf9f7;   /* 바닥 */
  --color-panel:   #ffffff;   /* 판 */
  --color-hair:    #e6e4df;   /* 판 테두리·헤어라인 */
  --color-rule:    #ececea;   /* 행 사이 연회색 괘선 */
  --color-rule-2:  #f1f0ec;   /* 더 연한 괘선(목록 안) */
  --color-ink:     #141414;   /* 먹 */
  --color-ink-body:#333333;
  --color-ink-sub: #4a4a46;
  --color-ink-g:   #55554f;   /* 회색 글 */
  --color-ink-dim: #6b6b67;   /* 흐림(대비 4.9:1) */
  --color-ink-mute:#737370;
  --color-ink-off: #8f8f8b;   /* 비활성 */
  --color-ink-ph:  #9b9a95;   /* placeholder */
  --color-ink-tick:#b8b6b0;   /* 제한 없음 점·회색 괘선 */
  --color-line:    #d8d6d0;   /* 글자 밑줄(기본) */
  --color-field:   #e3e1dc;   /* 입력·버튼 테두리 */
  --color-orange:  #f97316;   /* 선·밑줄·점·D-day≤7·마지막 숫자. 면 금지(로고 타일 예외) */
  --color-orange-ring: rgba(249, 115, 22, .14);
  --ease-sheet: cubic-bezier(.3, .7, .2, 1);
```

- [ ] **Step 2: 파일 끝에 공용 유틸 클래스 추가**

```css
/* ── 2026-10 리뉴얼 공용 유틸 ─────────────────────────────── */
/* 라벨 — 12px 회색 600. 한글 라벨에 자간·uppercase 없음 */
.t-k { font-size: 12px; font-weight: 600; color: var(--color-ink-dim); letter-spacing: 0; text-transform: none; }
/* 괘선 */
.rule-ink { border-bottom: 1px solid var(--color-ink); }
.hairline { border-bottom: 1px solid var(--color-hair); }
/* 숫자 */
.num { font-variant-numeric: tabular-nums; }
/* 글자 밑줄 링크 — 기본 회색, hover 주황 */
.u-link { border-bottom: 1px solid var(--color-line); transition: border-color .15s ease; }
.u-link:hover { border-bottom-color: var(--color-orange); }
/* 포커스 — 리뉴얼 부품 안에서는 주황 링 */
.rn :focus-visible { outline: 0; box-shadow: 0 0 0 4px var(--color-orange-ring); border-radius: 6px; }
/* 펼침 — display 토글 대신 grid-rows 0fr → 1fr (gen_split.py .x) */
.x-wrap { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows .4s var(--ease-sheet), padding .4s var(--ease-sheet), opacity .3s ease; }
.x-wrap[data-open="true"] { grid-template-rows: 1fr; opacity: 1; transition-delay: 0s, 0s, .1s; }
.x-wrap > * { min-height: 0; overflow: hidden; }
@media (prefers-reduced-motion: reduce) { .x-wrap { transition: none; } }
```

- [ ] **Step 3: 빌드로 토큰 유효성 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npm run build 2>&1 | tail -5
```
Expected: `✓ Compiled successfully` 포함, 오류 없음

- [ ] **Step 4: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/app/globals.css && git commit -m "feat(renewal): 리뉴얼 토큰(paper·panel·hair·rule·ink 단계·orange) + 공용 유틸 클래스"
```

---

### Task 3: Logo

**Files:**
- Create: `frontend/src/components/Logo.tsx`

- [ ] **Step 1: 구현** — 기하는 `docs/design/brand/README.md` 그대로(획 11, 틈 5, 타일 rx 22%)

```tsx
// frontend/src/components/Logo.tsx
import { cn } from "@/lib/utils";

/** 마크 — ㄱㄴ 틀 "찰칵". currentColor. 20px 미만은 Mark16. (docs/design/brand/mark.svg) */
export function Mark({ className, size = 22 }: { className?: string; size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} fill="none" aria-hidden="true" className={className}>
      <path d="M30 14 H50 V34 M14 30 V50 H34" stroke="currentColor" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 16px 정수 격자 쌍둥이 — 획 3, 틈 1, 둥근 끝 없음. (brand/mark-16.svg) */
export function Mark16({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" width={16} height={16} aria-hidden="true" className={className}>
      <path d="M6 2h8v3H6zM11 2h3v8h-3zM2 6h3v8H2zM2 11h8v3H2z" fill="currentColor" />
    </svg>
  );
}

/** 주황 타일 + 흰 마크 — "주황은 선" 규칙의 유일한 예외(로고 타일). nav 22 · 히어로 48. (brand/tile.svg) */
export function Tile({ size = 22, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" className={className}>
      <rect width="64" height="64" rx="14.08" fill="#f97316" />
      <path d="M30 14 H50 V34 M14 30 V50 H34" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 타일 22 + 조달핏(Pretendard 800, 16px, 자간 −0.035em). */
export function Lockup({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-ink font-extrabold text-[16px] tracking-[-0.035em] leading-none", className)}>
      <Tile size={22} />
      조달핏
    </span>
  );
}
```

- [ ] **Step 2: 타입 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep Logo || echo "ok"
```
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Logo.tsx && git commit -m "feat(renewal): Logo — Mark·Mark16·Tile·Lockup (brand/ 자산 그대로)"
```

---

### Task 4: Btn

**Files:**
- Create: `frontend/src/components/Btn.tsx`

- [ ] **Step 1: 구현** — 시안 `.bt`(36px, radius 8, 13px 600) / `.bt.dark` / `.bt.rv`(주황 헤어라인) / `.bt.txt`

```tsx
// frontend/src/components/Btn.tsx
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "dark" | "line" | "review" | "text";

const base = "inline-flex items-center justify-center h-9 px-3.5 rounded-[8px] text-[13px] font-semibold transition-colors duration-150 cursor-pointer select-none disabled:cursor-default";
const variants: Record<Variant, string> = {
  dark: "bg-ink text-white border border-ink hover:bg-[#2a2a2a] disabled:bg-field disabled:border-field disabled:text-ink-off",
  line: "bg-panel text-ink border border-field hover:border-orange",
  review: "bg-panel text-ink border border-orange data-[on=true]:text-ink-g data-[on=true]:border-field data-[on=true]:cursor-default",
  text: "h-auto px-1 text-ink-g font-medium border-0 [&>u]:no-underline [&>u]:border-b [&>u]:border-line hover:[&>u]:border-orange",
};

type Common = { variant?: Variant; className?: string; children: ReactNode; on?: boolean };
type AsLink = Common & { href: string } & Omit<ComponentProps<typeof Link>, "href" | "className" | "children">;
type AsButton = Common & { href?: undefined } & Omit<ComponentProps<"button">, "className" | "children">;

/** 링크면 <a>(Next Link), 아니면 <button>. shadcn Button 은 asChild 가 없어 링크에 못 쓴다. */
export function Btn(props: AsLink | AsButton) {
  const { variant = "line", className, children, on, ...rest } = props;
  const cls = cn(base, variants[variant], className);
  if ("href" in rest && rest.href) {
    const { href, ...a } = rest as AsLink;
    return <Link href={href} className={cls} data-on={on} {...a}>{children}</Link>;
  }
  const b = rest as AsButton;
  return <button type="button" className={cls} data-on={on} {...b}>{children}</button>;
}
```

- [ ] **Step 2: 타입 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep Btn || echo "ok"
```
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Btn.tsx && git commit -m "feat(renewal): Btn — dark·line·review·text, 링크/버튼 공용"
```

---

### Task 5: Nav

**Files:**
- Create: `frontend/src/components/Nav.tsx`

- [ ] **Step 1: 구현** — 시안 `gen_login.py::nav()`. 세션은 prop(`user`)으로 받고, 로그아웃 동작은 02 가 `onSignOut` 으로 넣는다(여기선 `/logout` 링크 자리만)

```tsx
// frontend/src/components/Nav.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
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

/** 상단 nav — 비로그인 '로그인' / 로그인됨 you@… + 메뉴(저장한 회사 ★ · 검토함 · 설정 · 로그아웃). 390: 링크 숨김, 현재 페이지와 로그인만. */
export function Nav({ user, signOutHref = "/logout" }: { user?: NavUser | null; signOutHref?: string }) {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    addEventListener("click", close); addEventListener("keydown", esc);
    return () => { removeEventListener("click", close); removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div className="rn flex items-center justify-between py-[22px] text-[13px] text-ink-g">
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
            <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="menu"
              className="text-ink font-semibold border-b border-ink cursor-pointer">
              {user.email.split("@")[0]}@…
            </button>
            {open && (
              <div role="menu" className="absolute right-0 top-7 z-20 min-w-[240px] rounded-[10px] border border-hair bg-panel p-1.5 text-left font-normal shadow-[0_8px_24px_rgba(20,20,20,.06)] max-sm:-right-2">
                <div className="px-3 py-2 text-[13.5px] text-ink">{user.email}<small className="block text-[12px] text-ink-mute">로그인됨</small></div>
                <div className="my-1.5 h-px bg-rule" />
                <span className="t-k block px-3 pb-0.5 pt-2">저장한 회사 {user.savedCompanies.length}</span>
                {user.savedCompanies.map((c) => (
                  <Link key={c.bizrnoNorm} role="menuitem" href={`/companies/${c.bizrnoNorm}`}
                    className="block rounded-md px-3 py-[7px] text-[13.5px] text-ink hover:bg-paper before:mr-2 before:text-[11px] before:text-orange before:content-['★']">
                    {c.name}
                  </Link>
                ))}
                <div className="my-1.5 h-px bg-rule" />
                <Link role="menuitem" href="/saved" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  검토함<small className="block text-[12px] text-ink-mute">검토한 공고 {user.reviewedCount}건</small>
                </Link>
                <Link role="menuitem" href="/settings" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  설정<small className="block text-[12px] text-ink-mute">비밀번호 변경 · 알림 수신 · 탈퇴</small>
                </Link>
                <div className="my-1.5 h-px bg-rule" />
                <Link role="menuitem" href={signOutHref} className="block rounded-md px-3 py-2 text-[13.5px] text-ink-mute hover:bg-paper">로그아웃</Link>
              </div>
            )}
          </div>
        ) : (
          <Link href={`/login?next=${encodeURIComponent(pathname || "/")}`} className="text-ink border-b border-ink">로그인</Link>
        )}
      </nav>
    </div>
  );
}
```

- [ ] **Step 2: 타입 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep "Nav.tsx" || echo "ok"
```
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Nav.tsx && git commit -m "feat(renewal): Nav — 로그인/로그인됨 메뉴(저장한 회사·검토함·설정·로그아웃), 세션은 prop"
```

---

### Task 6: SiteFooter · PageHead · Panel

**Files:**
- Create: `frontend/src/components/SiteFooter.tsx`
- Create: `frontend/src/components/PageHead.tsx`
- Create: `frontend/src/components/Panel.tsx`

- [ ] **Step 1: SiteFooter**

```tsx
// frontend/src/components/SiteFooter.tsx
import Link from "next/link";

/** 바닥 — 출처·갱신(카피 원칙: 상시 명시), 약관·개인정보·비공개 요청, 문의. 공문 톤. */
export function SiteFooter({ updatedAt }: { updatedAt?: string }) {
  return (
    <footer className="mt-16 border-t border-hair pt-6 pb-10 text-[12.5px] text-ink-mute leading-[1.7]">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <span>나라장터(국가종합전자조달) 공공데이터 기반 · 매일 05:00 갱신{updatedAt ? ` · 기준일 ${updatedAt}` : ""}</span>
        <span className="flex flex-wrap gap-x-4 gap-y-1">
          <Link href="/terms" className="u-link text-ink">이용약관</Link>
          <Link href="/privacy" className="u-link text-ink">개인정보처리방침</Link>
          <Link href="/privacy#company-optout" className="u-link">기업 정보 비공개 요청</Link>
          <a href="mailto:jsw7980@gmail.com?subject=%EC%A1%B0%EB%8B%AC%ED%95%8F%20%EB%AC%B8%EC%9D%98" className="u-link">문의</a>
        </span>
      </div>
      <p className="mt-2">추천은 검토 순서이며 낙찰을 예측하지 않습니다. © {new Date().getFullYear()} 조달핏</p>
    </footer>
  );
}
```

- [ ] **Step 2: PageHead**

```tsx
// frontend/src/components/PageHead.tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * 머리 — 제목 32 + 제목 옆 작은 글(사업자번호 등), aside(다른 회사·☆)는 h1 밖 형제(접근성 — 제목 이름에 버튼 글자가 섞이지 않게) / 메타 줄(· 구분) / children(걸러낸 경로·탭) / 아래 먹 괘선 하나.
 * 바닥(paper) 위에 놓인다. 판 밖.
 */
export function PageHead({ title, small, aside, meta, children, className }: {
  title: ReactNode; small?: ReactNode; aside?: ReactNode; meta?: ReactNode[]; children?: ReactNode; className?: string;
}) {
  return (
    <div className={cn("rule-ink pt-[26px] pb-[18px]", className)}>
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h1 className="m-0 flex flex-wrap items-baseline gap-x-3 text-[32px] max-sm:text-[24px] font-semibold tracking-[-0.035em] leading-[1.2] text-ink">
          <span>{title}</span>
          {small && <small className="text-[13px] font-normal tracking-normal text-ink-mute">{small}</small>}
        </h1>
        {aside}
      </div>
      {meta && meta.length > 0 && (
        <div className="mt-1.5 text-[14px] text-ink-g [&>span+span]:before:mx-2 [&>span+span]:before:text-[#c9c9c4] [&>span+span]:before:content-['·']">
          {meta.map((m, i) => <span key={i}>{m}</span>)}
        </div>
      )}
      {children}
    </div>
  );
}
```

- [ ] **Step 3: Panel**

```tsx
// frontend/src/components/Panel.tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** 흰 판 — 14px(390: 12px), 헤어라인. 결과·회사·검토함·로그인이 전부 이 판 하나를 반복한다. */
export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-[14px] max-sm:rounded-[12px] border border-hair bg-panel px-7 pb-7 pt-1.5 max-sm:px-4 max-sm:pb-5 max-sm:pt-0", className)}>
      {children}
    </section>
  );
}

/** 판 안 제목 줄 — 제목 16 + 작은 글 / 오른쪽 요약(· 구분). 아래 먹 괘선. */
export function PanelHead({ title, small, summary, className }: {
  title: ReactNode; small?: ReactNode; summary?: ReactNode[]; className?: string;
}) {
  return (
    <div className={cn("rule-ink flex flex-wrap items-baseline justify-between gap-5 pt-[22px] pb-3", className)}>
      <h2 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-ink">
        {title}{small && <small className="ml-2 text-[13.5px] font-normal text-ink-dim">{small}</small>}
      </h2>
      {summary && summary.length > 0 && (
        <div className="text-[13.5px] text-ink-g [&_b]:font-semibold [&_b]:text-ink [&>span+span]:before:mx-2 [&>span+span]:before:text-[#c9c9c4] [&>span+span]:before:content-['·']">
          {summary.map((s, i) => <span key={i}>{s}</span>)}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 타입 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "SiteFooter|PageHead|Panel" || echo "ok"
```
Expected: `ok`

- [ ] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/SiteFooter.tsx frontend/src/components/PageHead.tsx frontend/src/components/Panel.tsx && git commit -m "feat(renewal): SiteFooter · PageHead · Panel/PanelHead"
```

---

### Task 7: Sheet (표 행 · 펼침 · 흐림)

**Files:**
- Create: `frontend/src/components/Sheet.tsx`

- [ ] **Step 1: 구현** — 값은 `gen_split.py::SPLIT_CSS` 의 `.th/.tr/.sub/.x` 와 `gen_results_final.py::CSS` 가독성 패스(제목 16 / 둘째 줄 13.5 / 행 패딩 16 / 마감·추정가 15)

> Task 2 품질 검토 지적: `.x-wrap > * { overflow:hidden }` 이 펼침 안 버튼의 포커스 링(4px box-shadow)을 왼쪽 가장자리에서 자른다. 펼침 안쪽 `<div>` 에 `px-1 -mx-1 pb-1` 을 주어 링이 들어갈 여백을 만든다(아래 코드에 반영됨).

```tsx
// frontend/src/components/Sheet.tsx
"use client";

import { useId, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[28px_minmax(0,1fr)_84px_72px] gap-x-3 items-start max-sm:grid-cols-[minmax(0,1fr)_auto]";

/** 열 머리 — 390 에서는 숨긴다(두 줄 표). */
export function SheetHead({ cols = ["#", "공고 · 발주기관 · 근거", "마감", "추정가"] }: { cols?: string[] }) {
  return (
    <div className={cn(GRID, "rule-ink pb-2 pt-2.5 text-[12px] font-semibold text-ink-dim max-sm:hidden")}>
      {cols.map((c, i) => <span key={i} className={i >= 2 ? "text-right" : ""}>{c}</span>)}
    </div>
  );
}

export type SheetRowProps = {
  no: number;
  title: ReactNode;
  org: ReactNode;          // 둘째 줄 왼쪽
  why?: ReactNode;         // 둘째 줄 근거 칩(가장 강한 신호 1개)
  dLeft: { days: number; month: number; day: number };
  price: string;           // won()
  reviewed?: boolean;      // 왼쪽 주황 괘선
  defaultOpen?: boolean;
  children?: ReactNode;    // SheetExpand
  href?: string;           // 제목 링크(공고 상세). 없으면 행 클릭 = 펼침
};

/** 표 행 — 번호 · 제목/둘째 줄 · 마감 · 추정가. 번호 칸의 버튼이 펼침 토글(키보드·AT), 행 클릭은 마우스 편의. 검토한 행은 왼쪽에 주황 괘선 2px. */
export function SheetRow({ no, title, org, why, dLeft, price, reviewed, defaultOpen = false, children, href }: SheetRowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const hot = dLeft.days <= 7;
  const toggle = () => setOpen((v) => !v);
  return (
    <>
      <div data-sheet-row onClick={children ? toggle : undefined}
        className={cn(GRID, "relative border-b border-rule py-4 text-[14px] max-sm:py-3", children && "cursor-pointer",
          "before:absolute before:-left-4 before:top-0 before:bottom-0 before:w-0.5 before:origin-top before:bg-orange before:transition-transform before:duration-300 before:[transition-timing-function:var(--ease-sheet)]",
          reviewed ? "before:scale-y-100" : "before:scale-y-0")}>
        {children ? (
          <button type="button" aria-expanded={open} aria-controls={panelId} aria-label={`${no}번 공고 ${open ? "접기" : "펼치기"}`}
            onClick={(e) => { e.stopPropagation(); toggle(); }}
            className="num cursor-pointer self-start pt-[3px] text-left text-[12px] text-ink-off max-sm:sr-only">
            {String(no).padStart(2, "0")}
          </button>
        ) : (
          <span className="pt-[3px] text-[12px] text-ink-off max-sm:hidden">{String(no).padStart(2, "0")}</span>
        )}
        <span className="min-w-0">
          <span className="block text-[16px] font-semibold leading-[1.4] text-ink max-sm:text-[15px]">
            {href ? <a href={href} onClick={(e) => e.stopPropagation()} className="hover:border-b hover:border-orange">{title}</a> : title}
          </span>
          <span className="mt-1 block truncate text-[13.5px] text-ink-sub max-sm:whitespace-normal max-sm:text-[13px]">
            {org}{why && <span className="text-ink-dim before:mx-1.5 before:text-[#c9c9c4] before:content-['·']">{why}</span>}
          </span>
        </span>
        <span className={cn("num pt-0.5 text-right text-[15px] font-semibold", hot ? "text-orange" : "text-ink")}>
          D-{dLeft.days}<small className="ml-1.5 text-[12.5px] font-normal text-ink-mute">{dLeft.month}.{String(dLeft.day).padStart(2, "0")}</small>
        </span>
        <span className="num pt-0.5 text-right text-[15px] max-sm:hidden">{price}</span>
      </div>
      {children && (
        <div id={panelId} className={cn("x-wrap pl-10 max-sm:pl-0", open && "border-b border-rule pb-6 pt-4")} data-open={open}>
          <div className="-mx-1 px-1 pb-1">{children}</div>
        </div>
      )}
    </>
  );
}

export type QualLine = { state: "ok" | "none" | "warn" | "todo"; text: string };

/** 펼침 — 참가 자격(충족 ✓ 먹 600 > 제한 없음 회색 무표식 > 불충족 ✕ 주황) / 추천 근거 / 버튼 줄. */
export function SheetExpand({ quals, whys, actions }: { quals: QualLine[]; whys: ReactNode[]; actions?: ReactNode }) {
  return (
    <div className="grid grid-cols-[1fr_1.2fr] gap-7 max-sm:grid-cols-1 max-sm:gap-[18px]">
      <div>
        <span className="t-k mb-2 block">참가 자격</span>
        <ul className="m-0 list-none p-0">
          {quals.map((q, i) => (
            <li key={i} className={cn("py-1 text-[14px] leading-[1.7]",
              q.state === "ok" && "font-semibold text-ink after:ml-1.5 after:content-['✓']",
              q.state === "none" && "text-ink-mute",
              q.state === "warn" && "text-ink after:ml-1.5 after:font-bold after:text-orange after:content-['✕']",
              q.state === "todo" && "text-ink-mute")}>{q.text}</li>
          ))}
        </ul>
      </div>
      <div>
        <span className="t-k mb-2 block">추천 근거</span>
        <ul className="m-0 list-none p-0">{whys.map((w, i) => <li key={i} className="py-1 text-[14px] leading-[1.7] text-ink-body">{w}</li>)}</ul>
      </div>
      {actions && <div className="col-span-full flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** 흐림 묶음 — 게이트 뒤 6건째부터. 글자는 읽히지 않되 존재는 보인다. inert 로 포커스·클릭·AT 전부 차단(게이트 우회 방지). */
export function SheetFade({ children, off = false }: { children: ReactNode; off?: boolean }) {
  return <div className={cn(!off && "[&>*]:opacity-[.32] [&>*]:blur-[1.5px]")} inert={!off}>{children}</div>;
}
```

- [ ] **Step 2: 타입 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep "Sheet.tsx" || echo "ok"
```
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Sheet.tsx && git commit -m "feat(renewal): Sheet — 행·펼침(자격 세 상태·근거)·흐림, 390 두 줄"
```

---

### Task 8: Gate

**Files:**
- Create: `frontend/src/components/Gate.tsx`

- [ ] **Step 1: 구현** — 시안 `gen_login.py::gate_auth`. 옛 "이메일 등록" 한 칸은 폐기.

```tsx
// frontend/src/components/Gate.tsx
import { Btn } from "@/components/Btn";

/** 표 안 게이트 — 5건 뒤. "나머지 N건은 로그인 후 공개" + 로그인 / 회원가입. 끝나면 next 로 돌아온다. */
export function Gate({ rest, next }: { rest: number; next: string }) {
  const q = `?next=${encodeURIComponent(next)}`;
  return (
    <div className="hairline flex flex-wrap items-center gap-3.5 py-6 text-[14.5px]">
      <div>
        <b className="font-semibold text-ink">나머지 {rest}건은 로그인 후 공개</b>
        <span className="mt-1 block text-[13.5px] text-ink-dim">상위 5건은 로그인 없이 공개</span>
      </div>
      <span className="flex-1" />
      <span className="flex gap-1.5 max-sm:w-full">
        <Btn href={`/login${q}`} variant="line">로그인</Btn>
        <Btn href={`/signup${q}`} variant="dark">회원가입</Btn>
      </span>
    </div>
  );
}
```

- [ ] **Step 2: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/components/Gate.tsx && git commit -m "feat(renewal): Gate — 로그인/회원가입 두 버튼"
```

---

### Task 9: 전시 페이지 `/dev/foundation`

**Files:**
- Create: `frontend/src/app/dev/foundation/page.tsx`

- [ ] **Step 1: 구현** — 부품을 전부 한 번씩, 실제 공고명·숫자는 `docs/design/data/sample.json` 의 첫 세 건을 그대로 적는다(목 데이터 금지 원칙 — 시안과 같은 실제 결과)

```tsx
// frontend/src/app/dev/foundation/page.tsx
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { Nav } from "@/components/Nav";
import { PageHead } from "@/components/PageHead";
import { Panel, PanelHead } from "@/components/Panel";
import { Sheet } from "./sheet";
import { SiteFooter } from "@/components/SiteFooter";

export const metadata: Metadata = { title: "foundation", robots: { index: false, follow: false } };

/** 부품 전시 — 09 컷오버에서 삭제. 값은 data/sample.json(한종산업개발, 2026-10-16 실제 추천) 첫 세 건. */
export default function FoundationPage() {
  return (
    <div className="rn bg-paper min-h-screen text-ink">
      <div className="mx-auto max-w-[1120px] px-5 pb-[120px]">
        <Nav user={{ email: "you@company.co.kr", savedCompanies: [{ bizrnoNorm: "1248177731", name: "한종산업개발 주식회사" }, { bizrnoNorm: "4128113667", name: "(유)금강환경" }], reviewedCount: 3 }} />
        <PageHead title="한종산업개발 주식회사" small="124-XX-X731" aside={<Btn variant="review" className="ml-3 h-[30px] text-[13px]">☆ 회사 저장</Btn>}
          meta={["경상남도 창원시", "등록업종 15", "공급물품 없음", "기준일 2026-10-16"]} />
        <Panel className="mt-[22px]">
          <PanelHead title="검토할 공고 12건" small="적합 순" />
          <Sheet />
        </Panel>
        <Panel className="mt-7">
          <PanelHead title="수주 이력" small="계약 7건 · 2026.06.26 ~ 2026.09.30" summary={[<>누적 <b>268.2억</b></>, <>주요 발주기관 경상남도 창원시</>]} />
          <p className="pt-4 text-[14px] text-ink-body">표 본문은 06 회사 계획에서.</p>
        </Panel>
        <div className="mt-7 flex flex-wrap gap-2">
          <Btn variant="dark">나라장터 원문</Btn><Btn variant="review">검토</Btn><Btn variant="review" on>검토함</Btn><Btn variant="line">수정 요청</Btn>
          <Btn variant="text"><u>취소 · Esc</u></Btn><Btn variant="dark" disabled>가입</Btn>
        </div>
        <SiteFooter updatedAt="2026-10-16" />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Sheet 전시 조각(클라이언트)** — 같은 폴더

```tsx
// frontend/src/app/dev/foundation/sheet.tsx
"use client";

import { Btn } from "@/components/Btn";
import { Gate } from "@/components/Gate";
import { SheetExpand, SheetFade, SheetHead, SheetRow } from "@/components/Sheet";
import { dLeft, won } from "@/lib/format";

const TODAY = new Date(2026, 9, 16);
// data/sample.json results[0..2] + fade 용 results[5]
const ROWS = [
  { no: 1, title: "송탄정수장 공업용수공급 시설공사(1공구)", org: "경기도 평택시 상하수도사업소", why: "재출현 기관", clse: "2026-10-29", price: 5025454546, reviewed: true,
    quals: [{ state: "none", text: "면허 — 제한 없음" }, { state: "none", text: "지역 — 제한 없음" }, { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" }] as const,
    whys: ["경기도 평택시 상하수도사업소 — 과거 거래 이력 있음", "추정가가 회사 평균 수주가의 1.08배 — 유사한 규모", "공고 내용과 회사 업종 설명 유사도 73%"] },
  { no: 2, title: "중랑물재생센터 제1처리장 관리대행", org: "서울특별시 물재생센터 중랑물재생센터", why: "업종·물품 일치", clse: "2026-11-25", price: 6106074545, reviewed: false, quals: [], whys: [] },
  { no: 3, title: "송탄정수장 공업용수공급 시설공사(2공구)", org: "경기도 평택시 상하수도사업소", why: "재출현 기관", clse: "2026-10-29", price: 7690000000, reviewed: false, quals: [], whys: [] },
];

export function Sheet() {
  return (
    <>
      <SheetHead />
      {ROWS.map((r) => (
        <SheetRow key={r.no} no={r.no} title={r.title} org={r.org} why={r.why} dLeft={dLeft(r.clse, TODAY)} price={won(r.price)} reviewed={r.reviewed} defaultOpen={r.no === 1}>
          {r.quals.length > 0 && (
            <SheetExpand quals={[...r.quals]} whys={r.whys} actions={<><Btn variant="dark" href="https://www.g2b.go.kr">나라장터 원문</Btn><Btn variant="review">검토</Btn></>} />
          )}
        </SheetRow>
      ))}
      <Gate rest={7} next="/dev/foundation" />
      <SheetFade>
        <SheetRow no={6} title="중랑물재생센터 일부시설물 관리대행" org="서울특별시 물재생센터 중랑물재생센터" why="업종·물품 일치" dLeft={dLeft("2026-11-24", TODAY)} price={won(19974684545)} />
        <SheetRow no={7} title="양산하수처리장 악취저감사업 실시설계용역" org="경상남도 양산시 상하수도사업소" why="지역 매칭" dLeft={dLeft("2026-10-20", TODAY)} price={won(58081818)} />
      </SheetFade>
    </>
  );
}
```

- [ ] **Step 3: 개발 서버로 열어 눈으로 확인**

```bash
cd C:/Dev/personal/jodalfit/frontend && npm run dev
```
브라우저 `http://localhost:3000/dev/foundation`. 확인: 바닥 `#faf9f7` 위 흰 판, 머리 아래 먹 괘선 하나, 1행 펼침, 게이트 두 버튼, 6·7행 흐림, 오른쪽 위 `you@…` 메뉴 열림, 390 폭에서 두 줄 표·추정가 열 숨김.

- [ ] **Step 4: lint·build**

```bash
cd C:/Dev/personal/jodalfit/frontend && npm run lint && npm run build 2>&1 | tail -3
```
Expected: lint 오류 0, `✓ Compiled successfully`

- [ ] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/src/app/dev && git commit -m "feat(renewal): /dev/foundation 부품 전시 페이지(noindex, 09 에서 삭제)"
```

---

### Task 10: Playwright 검증 스크립트

**Files:**
- Create: `frontend/scripts/check_foundation.py`
- Modify: `frontend/.gitignore` — `scripts/_shot_*.png` 추가

- [ ] **Step 1: 스크립트** — 시안 `--check` 의 규칙을 옮긴다. 개발 서버가 떠 있어야 한다.

```python
# frontend/scripts/check_foundation.py
"""/dev/foundation 검증 — 금지어 0 · 인주 0 · 주황 면 0(로고 타일 제외) · 핵심 요소 · 펼침 · 메뉴 · 390.
실행: cd backend && uv run --no-sync python ../frontend/scripts/check_foundation.py  (frontend 에서 npm run dev 가 떠 있어야 한다)
주소: 환경변수 FOUNDATION_URL (기본 http://localhost:3000/dev/foundation)
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get("FOUNDATION_URL", "http://localhost:3000/dev/foundation")
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요", "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "아침 7시"]
OUT = Path(__file__).resolve().parent

def main():
    exe = next(Path.home().glob("AppData/Local/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), None)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=str(exe) if exe else None)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); pg.goto(URL); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(500)
        txt = pg.evaluate("document.body.innerText"); bad = [w for w in BANNED if w in txt]; assert not bad, f"금지어 {bad}"
        s = pg.evaluate("""() => { const cs = e => getComputedStyle(e);
            // 주황 면 금지 — 실제 요소의 배경만 본다. ::before/::after 는 못 본다(검토 행 왼쪽 2px 괘선 before:bg-orange 는 '선'이라 허용 대상)
            const orangeFaces = [...document.querySelectorAll('body *')].filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)' && !e.closest('svg')).length;
            // 인주 #e8431b 금지 — border 는 shorthand 가 아니라 네 변 longhand 로 본다(한 변만 색이 있으면 shorthand 는 다중값이라 못 잡는다)
            const injuk = [...document.querySelectorAll('body *')].some(e => { const c = cs(e); return [c.color, c.backgroundColor, c.borderTopColor, c.borderRightColor, c.borderBottomColor, c.borderLeftColor].includes('rgb(232, 67, 27)'); });
            const h1 = document.querySelector('h1'); const head = h1.closest('.rule-ink');
            return { bg: cs(document.querySelector('.rn')).backgroundColor, orangeFaces, injuk,
              rule: cs(head).borderBottomColor, h1: cs(h1).fontSize, panel: cs(document.querySelector('section')).backgroundColor, radius: cs(document.querySelector('section')).borderRadius,
              rows: document.querySelectorAll('button.num[aria-expanded]').length, open: document.querySelectorAll('.x-wrap[data-open=true]').length,
              gateBtns: document.querySelectorAll('a[href^="/login"], a[href^="/signup"]').length, fade: document.querySelectorAll('[inert] > [data-sheet-row]').length,
              me: !!document.querySelector('button[aria-haspopup=menu]') } }""")
        assert s["bg"] == "rgb(250, 249, 247)" and s["orangeFaces"] == 0 and not s["injuk"], s
        assert s["rule"] == "rgb(20, 20, 20)" and s["h1"] == "32px" and s["panel"] == "rgb(255, 255, 255)" and s["radius"] == "14px", s
        assert s["rows"] >= 1 and s["open"] == 1 and s["gateBtns"] == 2 and s["fade"] >= 2 and s["me"], s   # 게이트 두 버튼(로그인됨이라 nav 에는 로그인 링크 없음)
        pg.click("button[aria-haspopup=menu]"); pg.wait_for_timeout(150)
        m = pg.evaluate("document.querySelectorAll('[role=menu] [role=menuitem]').length"); assert m == 5, m
        pg.keyboard.press("Escape"); assert pg.evaluate("!document.querySelector('[role=menu]')")
        pg.locator("button.num[aria-expanded]").first.click(); pg.wait_for_timeout(500)   # 1행 접힘
        assert pg.evaluate("document.querySelectorAll('.x-wrap[data-open=true]').length") == 0
        pg.screenshot(path=str(OUT / "_shot_foundation.png"), full_page=True)
        pg.set_viewport_size({"width": 390, "height": 844}); pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(300)
        mo = pg.evaluate("""() => ({ overflow: document.documentElement.scrollWidth > 390, radius: getComputedStyle(document.querySelector('section')).borderRadius,
            priceHidden: getComputedStyle(document.querySelector('[data-sheet-row]').children[3]).display === 'none', me: getComputedStyle(document.querySelector('button[aria-haspopup=menu]')).display !== 'none' })""")
        assert not mo["overflow"] and mo["radius"] == "12px" and mo["priceHidden"] and mo["me"], mo
        pg.screenshot(path=str(OUT / "_shot_foundation_390.png"), full_page=True)
        b.close()
    print("ok foundation: tokens · head rule · panel · sheet(open/close) · gate · fade · nav menu(5) · 390")

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: .gitignore**

```
# frontend/.gitignore 끝에 추가
scripts/_shot_*.png
```

- [ ] **Step 3: 실행** — 터미널 1 `npm run dev`, 터미널 2:

```bash
cd C:/Dev/personal/jodalfit/backend && uv run --no-sync python ../frontend/scripts/check_foundation.py
```
Expected: `ok foundation: …`. 실패하면 메시지의 dict 를 보고 해당 컴포넌트를 고친 뒤 다시 실행한다(스크립트를 느슨하게 만들지 않는다).

- [ ] **Step 4: 캡처 눈으로 확인** — `frontend/scripts/_shot_foundation.png` 를 `docs/design/prototypes/_shot_final_default.png` 와 나란히 놓고 글자 크기·괘선·여백이 같은지 본다. 다르면 토큰이 아니라 컴포넌트 값을 고친다.

- [ ] **Step 5: 커밋**

```bash
cd C:/Dev/personal/jodalfit && git add frontend/scripts/check_foundation.py frontend/.gitignore && git commit -m "test(renewal): /dev/foundation Playwright 검증(금지어·인주·주황 면·요소·390)"
```

---

### Task 11: 마무리 — 푸시·README 기록

**Files:**
- Modify: `docs/design/README.md` — 끝에 한 절

- [ ] **Step 1: README 에 구현 상태 기록**

```markdown
## 구현 — 01 foundation (2026-10-19, 브랜치 `renewal`)
토큰(`globals.css` `--color-paper … --color-orange`, `--ease-sheet`)과 공용 부품(`Logo` `Btn` `Nav` `SiteFooter` `PageHead` `Panel/PanelHead` `Sheet/SheetRow/SheetExpand/SheetFade` `Gate`), 포맷 유틸(`lib/format.ts`, `node --test`)을 넣었다. 전시 `/dev/foundation`(noindex) + `scripts/check_foundation.py`. 옛 `gc-*` 토큰·`Header`·`Footer`·`Brand`는 09 컷오버에서 삭제. 운영(main)은 아직 에메랄드.
```

- [ ] **Step 2: 푸시**

```bash
cd C:/Dev/personal/jodalfit && git add docs/design/README.md && git commit -m "docs(design): 구현 01 foundation 기록" && git push origin renewal
```

---

## 자체 검토

- 시안 문법 ↔ 태스크: 바닥·판(2·6), 먹 괘선 하나(6 PageHead·PanelHead), 주황은 선(2 토큰 주석 + 10 검증 `orangeFaces == 0`), 글자 단계(6·7 값), 공문 톤·금지어(10), 자격 세 상태(7 SheetExpand), 검토 괘선(7 reviewed), 게이트 두 버튼(8), nav 로그인/메뉴(5), 로고 자산(3), 390 규칙(7·10). 포맷 규칙 won/dLeft/ymd/rgnBase(1).
- 플레이스홀더 없음. 모든 코드 블록 완전.
- 이름 일치: `Btn` variant `dark|line|review|text` 를 9·8 에서 그대로 씀. `SheetRow` prop `dLeft`(객체)·`price`(문자열) 를 9 에서 `dLeft()`·`won()` 으로 공급. `NavUser` 필드 `savedCompanies{bizrnoNorm,name}`·`reviewedCount` 를 9 에서 그대로. `.x-wrap[data-open]` 을 7·10 이 같이 씀.
- 02 가 이어받는 접점: `Nav` 의 `user` prop 과 `signOutHref`, `Gate` 의 `/login?next=`·`/signup?next=` 경로, `SiteFooter` 의 `/terms` 링크.
