# 디자인 리뉴얼 구현 — 마스터 계획 (순서·경계·공통 결정)

> **For agentic workers:** 이 문서는 서브 계획 9개의 순서와 공통 결정만 담는다. 실제 작업은 `2026-10-19-renewal-0N-*.md` 각 서브 계획을 superpowers:subagent-driven-development 또는 superpowers:executing-plans 로 실행한다. 서브 계획은 앞 번호가 끝나야 시작한다(의존 표 참조).

**Goal:** `docs/design/prototypes/*-final.html` 시안 7개(입구·결과·공고 상세·회사·로그인/회원가입·검토함·개선 기록)를 운영 프론트(Next.js 16)에 옮기고, 그에 필요한 인증·저장 데이터·백엔드 분기를 붙여 **한 번에** 배포한다.

**Architecture:** 시안의 문법(바닥 `#faf9f7` + 흰 판 14px, 먹 괘선 하나, 주황 `#f97316`은 선으로만, 글자 단계 12 / 13.5 / 14 / 16, 공문 톤)을 Tailwind v4 토큰과 공용 부품(Nav·Panel·Sheet·Gate)으로 먼저 깔고, 그 위에 페이지를 하나씩 올린다. 인증은 Supabase Auth(이메일+비밀번호, 확인 메일, 재설정)를 `@supabase/ssr` 쿠키 세션으로, 사용자 데이터(저장한 회사·검토한 공고·동의·회사 설명)는 RLS 테이블에 사용자 세션(anon 키)으로 읽고 쓴다. 기존 SEO URL(`/companies/[bizrno]`, `/notices/[no]`)·SSR 구조·JSON-LD·sitemap 은 그대로 둔다.

**Tech Stack:** Next.js 16 App Router(`proxy.ts`, Server Components) · Tailwind v4 `@theme` · shadcn base-nova(`Button` asChild 없음) · Supabase Auth + `@supabase/ssr` 0.10 · Postgres RLS(migrations 0052~) · FastAPI(`/recommendations/stream` 진행 이벤트, 회사 설명 기반 키워드 추천 분기) · Resend SMTP(확인·재설정 메일) · Playwright(backend venv)로 화면 검증.

---

## 1. 서브 계획과 순서

| # | 계획 | 산출물 | 의존 | 시안 |
|---|---|---|---|---|
| 01 | **foundation** — 토큰·셸·공용 부품 | `globals.css` 새 토큰, `Nav`(로그인 상태 자리만), `Footer`, `Panel`, `Sheet/SheetRow`(표 행 + 펼침), `Gate`, `Pill`(알약 없음 — 운영엔 없다), 글자 단계 유틸, 390 규칙 | — | 전부 |
| 02 | **auth** — 로그인·회원가입·재설정 | Supabase Auth 설정(확인 메일 필수, 링크 60분), Resend SMTP, `proxy.ts` 세션 갱신, `/login` `/signup` `/signup/sent` `/auth/confirm` `/reset` `/reset/new`, `user_consents` 테이블(0052), `/terms` 틀, Nav 로그인 상태(메뉴) | 01 | login-final |
| 03 | **saved** — 저장한 회사·검토한 공고·검토함 | `saved_companies`·`reviewed_notices` 테이블(0054, RLS), `StarCompany` ☆ 버튼, `ReviewButton` 검토, `/saved`(공고/저장한 회사 탭), Nav 메뉴 ★ 목록 | 02 | saved-final |
| 04 | **entry** — 입구(랜딩) | `/` 교체: 검색 상자 하나(콤보박스 회사·키워드 행), 오늘 등록된 공고 세로 틱, 최근 조회 칩(localStorage) | 01 | entry-simple |
| 05 | **results** — 결과 페이지 | `/recommendations` 교체: 머리(회사 이름·☆·다른 회사=상자) → 선 캔버스 머리 장면(실제 `/stream` 진행 이벤트에 묶음, 캐시 히트면 생략) → 두 단(회사 정보 sticky / 표 5건 + Gate + 흐림 7건) → 네 상태(0건·오류·로그인 뒤·검토 뒤), 종류 탭(사전규격·발주계획), 인쇄 뷰(report) | 01 02 03 | results-final, flow, report |
| 06 | **company** — 회사 페이지 | `/companies/[bizrno]` 본문 교체(URL·메타·JSON-LD·noindex 규칙 유지): 머리·걸러낸 경로·추천 판(계산 중 상태)·수주 이력 판·낙찰 판(투찰률 눈금)·같은 시장 낙찰 회사, 폐업이면 추천 중단, 벡터·이력 없으면 **분석 요청**(`company_descriptions` 0055 + 백엔드 설명 기반 키워드 추천 분기) | 01 02 03 05 | company-final |
| 07 | **notice** — 공고 상세 | `/notices/[no]` 본문 교체(URL·JSON-LD 유지): 레일(마감·자격 세 상태·수치) + 본문(과업·조건·단계·기관·정정), 지역 판정은 `qualifications.region_allows` 와 같은 규칙(백엔드 `/qualifications/check` 사용) | 01 02 03 | notice-final |
| 08 | **changelog** — 개선 기록 | `/changelog`: 빌드 때 `docs/recommender/changelog.md` → 페이지(최신순 타임라인, 머리 숫자 셋 + 틀 문장, "어떻게 고르는가" 판은 `score.py` 상수에서 생성, HIDE·측정 전·해 보고 뺀 것) | 01 | changelog-final |
| 09 | **cutover** — 스킨 교체·정리·배포 | `/about` `/privacy` `/terms` `/companies/browse` `/companies/industry` 스킨, 로고·파비콘·OG 교체(`docs/design/brand/`), 옛 컴포넌트·`DESIGN.md`·`world-gc` 삭제, 사업자번호 마스킹 통일, 문구 일괄 점검, Lighthouse ≥ 90, GSC·sitemap 확인, 배포 | 전부 | — |

실행 단위: 01 → 02 → 03 은 직렬. 04·08 은 01 뒤 언제든(병렬 가능). 05 는 03 뒤. 06·07 은 05 뒤(05 의 부품을 쓴다). 09 마지막.

## 2. 배포 전략 — 부분 선반영 금지

- 브랜치 `renewal` 하나에서 전부 작업. Vercel 프리뷰로 확인. 운영(`main`)은 리뉴얼이 통째로 준비될 때까지 에메랄드 그대로(`docs/design/README.md` 결정).
- 백엔드·DB 변경(0052~0055, 설명 기반 추천 분기, `/qualifications/check`)은 **운영에 먼저 적용해도 무해**하다(새 테이블·새 분기). 프론트 컷오버 전에 적용해 둔다.
- Supabase Auth 켜기·Resend 도메인 인증은 프리뷰 단계에서 끝낸다(확인 메일이 실제로 와야 02 를 끝낼 수 있다).
- 컷오버 = `renewal` → `main` PR 하나. 되돌리기 = PR revert.

## 3. 공통 결정 (서브 계획이 전제하는 것)

### 3.1 토큰 (01 에서 확정, 이후 변경 금지)
```
바닥 #faf9f7 · 판 #fff · 헤어라인 #e6e4df · 연회색 괘선 #ececea · 먹 괘선 #141414
글자: 먹 #141414 · 본문 #333 · 보조 #4a4a46 · 회색 #55554f · 흐림 #6b6b67 / #737370 · 비활성 #8f8f8b / #9b9a95
주황 #f97316 — 선·밑줄·점·괘선·D-day≤7·마지막 숫자에만. 면 금지(예외: 로고 타일)
글자 단계 12 / 13.5 / 14 / 16 · 제목 32(회사 이름)·28(경로 숫자)·34(마지막 숫자) · 한글 라벨에 자간·uppercase 없음
곡선 cubic-bezier(.3,.7,.2,1) · 판 radius 14px(390: 12px) · 폰트 Pretendard Variable 만(Noto Serif KR 제거)
```
시안 CSS 의 원천: `docs/design/scripts/gen_results_v3.py::BASE/SHEET_CSS`, `gen_split.py::SPLIT_CSS`, `gen_results_final.py::CSS`, 각 `gen_*.py` 의 `CSS`. 값은 거기서 옮긴다.

### 3.2 인증
- Supabase Auth, **이메일 + 비밀번호(8자 이상, 조합 규칙 없음)**. 가입 시 확인 메일 필수(Confirm email ON), 링크 유효 60분·1회. 재설정은 recovery 메일.
- `next` 되돌아가기 파라미터(Gate·Nav 가 붙인다)는 **상대 경로(`/`로 시작, `//`·`http` 금지)만 허용**하고 아니면 `/recommendations` 로 — 오픈 리다이렉트 방지. 검증 함수 `lib/safe-next.ts` 하나에 두고 로그인·회원가입·확인 콜백이 전부 그것만 쓴다.
- 세션은 `@supabase/ssr` 쿠키. `src/proxy.ts` 가 매 요청 세션을 갱신(Next 16: `middleware` 아님). 보호 경로는 `/saved` 하나(비로그인이면 안내 판, 리다이렉트 아님 — 시안 그대로).
- 동의: 이용약관(필수)·개인정보(필수)·알림 메일(선택) → `user_consents(user_id, terms_version, privacy_version, marketing_opt_in, consented_at)`. 버전은 `lib/privacy.ts::PRIVACY_VERSION` 와 새로 두는 `TERMS_VERSION`.
- 메일 발신 `noreply@jodalfit.co.kr`(Resend, SPF/DKIM). 제목 "조달핏 이메일 확인 (60분 유효)" / "조달핏 비밀번호 재설정 (60분 유효)". 본문은 시안 `gen_login.py::scene_mail` 문구.
- 이름·연락처·사업자번호는 받지 않는다. "회원가입"은 쓰되 "매직링크"·"이메일 구독" 문구는 전 페이지에서 없앤다.

### 3.3 사용자 데이터 (RLS, 사용자 세션으로 접근)
```sql
-- 0052 user_consents (02)
-- 0054 saved_companies(user_id, bizrno_norm, created_at) PK(user_id, bizrno_norm)
--      reviewed_notices(user_id, bid_ntce_no, bid_ntce_ord, via_bizrno_norm, created_at) PK(user_id, bid_ntce_no, bid_ntce_ord)
--      정책: auth.uid() = user_id 로 select/insert/delete. 마감 30일 지난 reviewed 행은 pg_cron 주 1회 삭제.
-- 0055 company_descriptions(bizrno_norm PK, description, email, created_at, updated_at) — 분석 요청. 익명 insert 는 백엔드(service_role)만.
```
프론트는 사용자 테이블을 **anon 키 + 세션**으로 접근(`lib/supabase-browser.ts`, `lib/supabase-session.ts` 신설). `lib/supabase-server.ts`(service_role)는 공개 데이터 SSR 전용으로 유지.

### 3.4 백엔드 변경 (05·06·07)
- `/recommendations/stream` 진행 이벤트가 네 단계(후보 검색 끝 → 자격 거르기 끝 → 점수·MMR 끝 → 설명)를 내보내는지 확인하고, 없으면 `stage` 이벤트 추가. 머리 장면은 이 이벤트에만 묶는다(가짜 진행률 금지).
- 회사 모드에서 벡터 없음 + `company_descriptions` 행 있음 → 그 설명으로 키워드 추천(자격 판정 없음, 응답에 `basis: "description"`).
- `POST /company-descriptions`(사업자번호·설명·이메일) — rate limit, bot_guard.
- `/qualifications/check` 를 공고 상세 레일 판정에 사용(이미 있음).

### 3.5 공통 문구 규칙 (09 에서 일괄 점검, 각 계획도 지킨다)
- 공문 톤, 명사형. 미사여구 금지(`docs/design/README.md` "문구" 결정). 금지어: 낼 수 있 / 왜 남았 / 맞아요 / 검토 인장 / 하는 일 / 넣으면 / 안 맞아요 / 이메일 구독 / 매직링크 / 회사 연결 / 해드려요 / 예요·에요 / 하세요 / 아침 7시 메일.
- 사업자번호 마스킹은 `lib/utils.ts::maskBizrno`(`137-XX-X4567`) 하나만.
- 참가 자격 표기: 충족(✓ 먹 600) > 제한 없음(회색, 표식 없음) > 불충족(✕ 주황).
- 지역 표시는 기초자치단체까지(`rgn_base` 규칙: 앞 두 토큰).
- 적합 점수 숫자 비노출. 근거는 유지.

### 3.6 검증 방법 (프론트에 테스트 프레임워크 없음)
- 각 계획의 마지막 태스크는 **Playwright 화면 검증 스크립트**(`frontend/scripts/check-<page>.py`, backend venv 의 playwright 사용, 시안의 `--check` 를 옮긴 것)로 끝난다: 금지어 0, 인주 0, 주황 면 0(배경색에 #f97316 쓴 요소 0 — 로고 타일 제외), 핵심 요소 존재, 390 가로 넘침 없음, 캡처.
- `npm run lint` · `npm run build` 통과. 빌드가 깨지면 커밋하지 않는다.
- 로직이 있는 유틸(마크다운 변환, 마스킹, 날짜 계산)은 `node --test` 로 파일 하나씩 검사(`frontend/src/lib/*.test.ts`, `tsx` 없이 `node --experimental-strip-types`).

## 3.7 01 foundation 최종 검토에서 02~09 로 넘긴 것 (2026-10-19)
- **02**: `Nav` 의 로그인 링크가 `usePathname()` 만 써서 쿼리(`?mode=keywords&q=…`)를 잃는다 → `useSearchParams()` 로 `next` 에 쿼리까지 담되, Next 16 에선 Suspense 경계가 필요하니 Nav 를 클라이언트 섬으로 감싼다. `Nav` 메뉴의 `role="menu"/"menuitem"` 은 화살표 이동·포커스 복귀가 없어 반쪽이다 → role 을 떼고 링크 팝오버로 두되 Escape 때 트리거로 포커스를 돌린다(`check_foundation.py` 의 `menuitem == 5` 도 링크 수로 바꾼다). `.rn bg-paper` 는 페이지마다 반복하지 말고 리뉴얼 레이아웃 하나에 둔다.
- **05~07**: `SheetFade.off`·`SheetHead.cols` 가 안 쓰이면 09 에서 지운다. `dLeft` 가 null 을 돌려주면 행은 `—`, 마감 지난 행은 회색 "마감"(01 에서 반영).
- **09**: 개인정보처리방침 8조(기업 정보 비공개 요청)에 본인 확인 한 줄 추가 — "회사 도메인 이메일 회신 또는 사업자등록증 사본(사업자번호 확인용)". 2026-10-20 제이엔지한섬엔지니어링(주) 문의를 계기로 결정(승우님: 리뉴얼 때 같이).
- **09**: `formatKRW`·`formatKRWFull`·`daysUntil` 을 옛 페이지와 함께 삭제(`won`·`wonFull`·`dLeft` 로 통일), 미사용 토큰(`ink-ph`·`ink-tick`·`rule-2`)·`Mark`/`Mark16` 사용 여부 점검, 검증 스크립트 이름을 `check_<page>.py` 로 통일.

## 4. 시안 ↔ 코드 대응 (옮길 때 보는 원천)

| 페이지 | 시안 HTML | 생성기(CSS·문구·동작의 원천) | 데이터 예시 |
|---|---|---|---|
| 입구 | `prototypes/final/entry-simple.html` | `scripts/gen_entry_simple.py`, 콤보박스 JS `gen_entry.py` | `fetch_today` 쿼리 |
| 결과 | `results-final.html`, `flow.html`, `report.html` | `gen_results_final.py`, `gen_flow.py`(ENGINE_JS·RUN_JS), `gen_split.py`, `gen_report.py` | `data/sample.json`, `funnel.json` |
| 공고 상세 | `notice-final.html` | `gen_notice_final.py`, `gen_notice.py`(l3 블록) | `gen_notice.fetch` |
| 회사 | `company-final.html` | `gen_company.py` | `data/company_{a,b,c,d}.json` |
| 로그인 | `login-final.html` | `gen_login.py` | — |
| 검토함 | `saved-final.html` | `gen_saved.py` | 위 둘 |
| 개선 기록 | `changelog-final.html` | `gen_changelog.py`(md 변환·HIDE·차이 표기·how_panel) | `docs/recommender/changelog.md` |

## 5. 서브 계획에 들어가지 않는 것 (범위 밖, 기록만)
- 아침 알림 메일 발송(Phase 4 보류). 수신 동의만 저장.
- 요금제·결제. 다부서(활동 영역) 블록. 공고 지도(`/explore`). "안 맞아요" 버튼.
- 주간 인사이트 `/insights` — 폐지, 홈으로 리다이렉트(09 에서 처리).

## 6. 완료 기준 (로드맵 Phase 3)
- 프리뷰에서 7개 페이지가 시안과 같은 문법으로 동작, 가입 → 로그인 → ☆ 저장 → 검토 → 검토함까지 1명 완주.
- Lighthouse 성능·접근성 ≥ 90(홈·결과·회사·공고).
- GSC: 컷오버 1주 뒤 회사·공고 페이지 색인 수 유지, sitemap 정상.
- PostHog: `search_submit` 대비 가입 완료·검토·☆ 이벤트 집계 시작(전후 비교 기준).
