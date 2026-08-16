---
name: 조달핏 — 개찰판(開札板)
description: 공공입찰 검토 우선순위를 공식 개찰판 문법으로 보여주는 청색 장부·괘선·인주 디자인 시스템
colors:
  paper: "#f6f8fb"
  sheet: "#ffffff"
  band: "#1e3a66"
  band-ink: "#c7d5ea"
  band-hi: "#f4f7fc"
  tint: "#e5edf8"
  tint-line: "#b9c9e0"
  tint-ink: "#2f4a75"
  ink: "#17233a"
  ink-2: "#3a4a66"
  ink-3: "#5c6b85"
  rule: "#d9e0ea"
  injuk: "#b23a2a"
  injuk-deep: "#93291b"
  injuk-soft: "#f2e3dc"
  amber: "#8a5b14"
typography:
  display:
    fontFamily: "Noto Serif KR, Nanum Myeongjo, Apple SD Gothic Neo, serif"
    fontSize: "30~34px (sm: 42~50px)"
    fontWeight: 900
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Noto Serif KR, Nanum Myeongjo, Apple SD Gothic Neo, serif"
    fontSize: "19px (sm: 21px), 구독대 23~27px"
    fontWeight: 900
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Pretendard Variable, Pretendard, sans-serif"
    fontSize: "15.5px (sm: 16.5px)"
    fontWeight: 700
    lineHeight: 1.45
  body:
    fontFamily: "Pretendard Variable, Pretendard, sans-serif"
    fontSize: "14px ~ 14.5px"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: "Pretendard Variable, Pretendard, sans-serif"
    fontSize: "11.5px ~ 13px"
    fontWeight: 700
rounded:
  rect: "3px"
  capsule: "999px"
components:
  button-band:
    backgroundColor: "{colors.band}"
    textColor: "{colors.band-hi}"
    rounded: "{rounded.rect}"
    height: "44px"
    padding: "0 20px"
  button-band-hover:
    backgroundColor: "{colors.ink}"
  button-on-band:
    backgroundColor: "{colors.band-hi}"
    textColor: "{colors.band}"
    rounded: "{rounded.rect}"
    height: "44px"
    padding: "0 16px"
  button-on-band-hover:
    backgroundColor: "#ffffff"
  button-stamp:
    textColor: "{colors.injuk}"
    rounded: "{rounded.rect}"
    height: "36px"
    padding: "0 14px"
  button-stamp-saved:
    backgroundColor: "{colors.injuk-soft}"
    textColor: "{colors.injuk-deep}"
  capsule-filter:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.capsule}"
    height: "28px"
    padding: "0 12px"
  capsule-filter-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  input-board:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.rect}"
    padding: "12px 16px"
---

# Design System: 조달핏 — 개찰판(開札板)

## Overview

**Creative North Star: "개찰판(開札板) — 청색 장부 렌디션"**

추천 결과는 카드 피드가 아니라 공식 개찰판이다. 봉인된 공고가 번호 행으로 도열하고, 행이 "개봉"되며 근거를 내보인다. SaaS 카드 대시보드 배치 — 부드러운 그림자 카드, 큰 라운드 — 를 명시적으로 거부한다. 물성은 관공서 장부다: 차가운 장부지(#F6F8FB) 지면 위 괘선 보드, 네이비(#1E3A66) 밴드가 판머리와 구독대를 소유하고, 청람 잉크(#17233A) 활자와 옅은 청색 틴트(#E5EDF8) 칩이 본문을 채운다. 인주(#B23A2A)는 마감 임박과 인장에만 남는 **유일한 붉은 사건**이다. (2026-08-16 사용자 확정 — 크라프트·서류지 렌디션에서 청색 장부로 전환.)

타이포그래피가 곧 인터페이스다: 명조(Noto Serif KR) 블랙 대활자가 판머리와 섹션 머리를 소유하고, Pretendard가 본문 워크호스를 맡으며, 모든 수치는 tabular numerals로 공유 괘선 위에 정렬된다. 장식 일러스트·아이콘 장식·장난스러운 톤은 금기다. 진지하되 촌스럽지 않은, "검토 우선순위"라는 프레이밍에 걸맞은 공식 문서의 절제가 기준이다.

**마이그레이션 경계 (2026-08-16 기준):** 색 축은 이미 사이트 전역이 하나다 — 레거시 토큰 블록(`--color-brand`, shadcn `:root`, `--color-score`, selection, focus)까지 전부 네이비/청람 계열로 재배선되었고, 차트 팔레트·OG 이미지·파비콘도 #1E3A66 축이다. 월드 **문법**(`.world-gc`, 괘선, 명조, 관인, 개봉)은 `/recommendations`·랜딩·Header에서 확립되었으며, `/notices`·`/companies`·`/insights`·Footer는 색만 이동했을 뿐 아직 구 문법(카드·그림자 유틸)으로 조판되어 있다 — 이들의 월드 문법 이관은 후속 라운드다. **새로 만들거나 리디자인하는 표면은 이 문서를 따른다.**

**Key Characteristics:**
- 카드가 아닌 행(行) — 번호 붙은 괘선 목록이 기본 단위
- 명조 900 대활자 + Pretendard 워크호스 + 전 수치 tabular
- 장부지·네이비 밴드·청람 잉크의 단색조 위계, 인주는 예약된 유일한 붉은색
- 봉인 → 개봉 → 인장이라는 상태 문법
- 그림자 없음, 깊이는 네이비 밴드와 괘선으로

## Colors

차가운 장부지 위 청람 잉크와 네이비 밴드 — 단일 청색 축의 단색조에, 인주 한 색만 사건으로 남긴 팔레트다.

### Primary
- **네이비 밴드 (band, #1E3A66):** 브랜드 축이자 영역의 주인 — 판머리·구독대 밴드 배경, 지면 위 주 버튼 배경, Header 활성 메뉴 밑줄, 랜딩 CTA 텍스트, 파비콘·OG의 PRIMARY. 데이터 시각화는 이 색의 순차 램프(#1E3A66 → #3D5F94 → #7591BD → #AEBFDA → #DBE4F1)를 쓴다.
- **청람 잉크 (ink, #17233A):** 활자의 먹. 본문 강조·제목·활성 캡슐 배경·굵은 괘선·포커스 아웃라인·주 버튼 hover.
- **잉크-2 (ink-2, #3A4A66):** 부제·기관명·보조 굵은 텍스트·보조 버튼 테두리.
- **잉크-3 (ink-3, #5C6B85):** 지면 위 muted 텍스트(대비 ≥4.5:1). 각주(※)·메타·플레이스홀더.

### Secondary
- **틴트 (tint, #E5EDF8):** 옅은 청색 채움 — 긍정 시그널·증거 칩 배경, 랜딩 배지, 활성 캡슐의 앞머리 점.
- **틴트 선 (tint-line, #B9C9E0):** 칩 테두리·절취선(dashed)·스크롤바 썸·텍스트 선택 틴트의 원색.
- **틴트 잉크 (tint-ink, #2F4A75):** 틴트 채움 위 텍스트 전용(대비 ≥4.5:1).
- **밴드 잉크 (band-ink, #C7D5EA):** 네이비 밴드 위 보조 텍스트·밑줄 입력 전용(대비 ≥4.5:1). 지면 위에서는 쓰지 않는다.
- **밴드 하이 (band-hi, #F4F7FC):** 네이비 밴드 위 제호·강조·주 버튼 글자. 밴드 위 반전 버튼의 배경.

### Tertiary
- **인주 (injuk, #B23A2A):** 도장의 붉은색. 사용처가 예약되어 있다 — 아래 규칙 참조.
- **인주 딥 (injuk-deep, #93291B):** 저장된 인장 버튼의 텍스트.
- **인주 소프트 (injuk-soft, #F2E3DC):** 인장 버튼 hover/저장 상태 배경.
- **관보 앰버 (amber, #8A5B14):** 마감 D-3~5 경계 텍스트와 골든타임(사전규격 의견 마감) 시맨틱 — 전 사이트 공통. 인주(D≤2)로 넘어가기 전의 완충색.

### Neutral
- **장부지 (paper, #F6F8FB):** 세계의 지면 — `.world-gc` 배경이자 활성 캡슐 위 글자색.
- **판 시트 (sheet, #FFFFFF):** 지면보다 밝은 면 — 개봉된 행 배경, 입력 필드, 비활성 캡슐, hover 면, 관인의 흰 지면 판.
- **괘선 (rule, #D9E0EA):** 1px hairline. 행 구분선·필터 바 경계·캡슐 테두리.

### Named Rules
**인주 예약 규칙.** 인주(#B23A2A)는 (1) 마감 임박 D≤2("오늘"/"D-1"/"의견 오늘 마감")과 (2) 인장·관인 — 관인 SVG, 검토 인장 스탬프, 인장 버튼, 저장 필터 캡슐의 점 — 에만 쓴다. 화면에서 유일한 붉은 사건이어야 하며, 청색 렌디션 전환과 함께 예외가 소멸했다(구 렌디션의 Header 활성 밑줄도 이제 네이비다). 일반 강조·링크·버튼에 붉은색 금지.

**밴드 단위 색 커밋 규칙.** 색은 요소 단위가 아니라 영역 단위로 commit한다 — 판머리·구독대는 네이비 밴드 전체, 본문은 장부지 전체. 밴드 위 텍스트는 반드시 `band-hi`(제호·강조) 또는 `band-ink`(보조)를 쓰고, 밴드는 괘선 없이 면 자체로 선다.

## Typography

**Display Font:** Noto Serif KR (fallback: Nanum Myeongjo, Apple SD Gothic Neo, serif) — 토큰 `--font-gc-serif`
**Body Font:** Pretendard Variable (fallback: system-ui 계열) — 토큰 `--font-sans`
**수치:** 별도 모노 서체 없음 — 본문 서체에 `font-variant-numeric: tabular-nums` + `"tnum"` 전역 적용

**Character:** 관보의 명조 블랙 표제와 실무 문서의 산세리프 본문. 명조는 900 웨이트로만, 자간 -0.02em로 조인다. 부드럽거나 친근한 라운드 서체는 이 세계에 없다.

### Hierarchy
- **Display** (명조 900, 판머리 30px → sm 42px / 랜딩 히어로 34px → sm 50px, lh 1.2, ls -0.02em): 판머리(BoardHead) 회사명·검색어와 랜딩 히어로 전용. `break-keep`. 밴드 위에서는 `band-hi`, 지면 위에서는 `ink`.
- **Headline** (명조 900, 19~27px, ls -0.02em): 섹션 머리(사전규격·발주계획·키워드 패널·랜딩 피처 행), 구독대 카피. 지면 위에서는 이중 괘선과 함께 등장한다.
- **Title** (Pretendard 700, 15.5px → sm 16.5px, lh 1.45): 행의 공고명. 닫힌 행에서는 데스크톱 1줄 truncate, 개봉 시 전체 노출.
- **Body** (Pretendard 400~500, 14~14.5px, lh 1.7~1.8): 총평·추천 근거·안내문. 최대 폭 60~72ch, `break-keep`.
- **Label** (Pretendard 600~700, 11.5~13px): 컬럼 머리·필터 그룹 라벨·각주·칩·메타.
- **Numeric** (tabular, 우측 정렬): 순번·마감·추정가·적합 % — 컬럼에서는 항상 오른쪽 정렬로 괘선을 공유한다.

### Named Rules
**명조 900 단일 웨이트 규칙.** 명조는 표제 전용이며 웨이트는 900(font-black) 하나만 쓴다. 본문·UI 컨트롤에 명조를 쓰지 않는다 (예외: 인장 내부 각자刻字).

**전 수치 tabular 규칙.** 화면의 모든 숫자 — 순번, D-day, 금액, %, 날짜 — 는 tabular numerals다. 순번은 2자리 zero-pad("01", "02")로 판의 대장 대열을 만든다.

## Layout

- **컨테이너:** 판·헤더는 `max-width 1080px`, 랜딩은 880px. 수평 패딩 20px(모바일) / 32px(sm 이상). 판머리·필터 바·본문·구독대가 모두 같은 컨테이너 축을 공유한다.
- **판 구조:** 단일 컬럼의 번호 행 목록(`<ol>`). 데스크톱 행 그리드는 `[48px | 1fr | 84px | 104px | 120px | 28px]` = 순번 | 공고 | 마감 | 추정가 | 적합 | 개봉 표식, `gap-x` 16px. 컬럼 머리는 데스크톱 전용이고 하단 2px 잉크 선으로 판을 연다.
- **모바일:** 수치 컬럼이 사라지고 마감·추정가·적합이 공고명 아래 메타 라인으로 접힌다(`[40px | 1fr | 28px]`). 판머리의 관인은 44px로 축소, 조회 폼은 판머리 하단으로 내려온다.
- **스티키 스택:** Header(h 64px, z-40) 아래 필터 바가 `top-16 z-30`으로 붙는다(`paper/95` + backdrop-blur).
- **수직 리듬:** 행 padding-y 14~16px, 섹션 간격 56px(`mt-14`), 판머리 상하 28~36px, 구독대 36~44px.
- **마감 축 단일화:** 마감·D-day는 행당 한 곳에만 표기한다(데스크톱 마감 컬럼 / 모바일 메타 라인).

## Elevation & Depth

**그림자 없음.** `.world-gc` 표면에 box-shadow가 존재하지 않는다. 깊이는 세 가지로만 만든다: (1) 색 밴드 — 네이비 밴드(판머리·구독대)가 장부지 본문을 위아래로 무겁게 눌러 잡고, 지면(paper) vs 시트(white)의 명도 차가 개봉면·입력면을 띄운다, (2) 괘선의 위계 — 2px+1px 이중 괘선 > 2px 잉크 선 > 1px hairline > dashed 절취선, (3) 스티키 바의 반투명 + backdrop-blur(그림자 대신 지면 비침). (레거시 `--shadow-*`·`.card-soft`는 미이관 표면의 잔여 유틸이며 이 시스템에 속하지 않는다.)

### Named Rules
**괘선 위계 규칙.** 이중 괘선(2px 잉크 + 3px 아래 1px 잉크, `.gc-double-rule`)은 장부지 위 판·섹션의 머리와 Header에만 쓴다. 네이비 밴드는 괘선 없이 면으로 선다. 2px 단일 잉크 선은 컬럼 머리 하단과 빈 판 테두리. 1px `rule` hairline은 행 구분. dashed `tint-line`은 절취선 — 개봉된 봉투의 뜯긴 자리 — 전용이다.

## Shapes

- **직사각형 3px:** 버튼·입력·textarea·칩·태그·모드 탭 등 모든 블록 요소는 `rounded-[3px]`. 공문서 인쇄물의 거의-각진 모서리.
- **캡슐(999px):** 필터 캡슐·제안 키워드 필·랜딩 배지 — 즉, 캡슐은 컨트롤·배지에만 허용. 정보 표시용 칩·태그는 3px 직사각형이다.
- **봉인 딱지:** 17×11px, `rounded-[1px]`, 네이비(band) 단색 — 테두리 없는 작은 인지. 닫힌 행의 아래 괘선(개봉될 이음선) 위에 걸쳐 앉는다.
- **인장:** 관인은 정방형 이중 테두리(외곽 4.5px + 내곽 1.5px), 검토 인장은 원형. 인장류는 항상 -4° 기울여 "찍힌" 자세로 둔다.
- **테두리 언어:** 면 대신 1px 테두리로 구획하는 것이 기본. 보조 버튼은 `ink-2` 1px 테두리 + 투명 배경.

### Named Rules
**종이 위 도장 규칙.** 도장은 어두운 밴드 위가 아니라 종이 위에 찍힌다 — 관인은 흰 지면 판(`sheet` 채움, 불투명도 0.95)을 깔고 네이비 밴드 위에 앉으며, 검토 인장은 `paper` 채움(0.85) 위에 인주 획을 얹는다. 인주 획을 어두운 배경에 직접 올리지 않는다.

## Components

### Buttons
- **Shape:** 거의 각진 직사각형 (3px). 높이 44px(주 액션, h-11) / 36px(행 내부, h-9) / 32px(판머리 compact, h-8).
- **밴드 버튼 (primary, 지면 위):** `band` 배경 + `band-hi` 글자, 700 웨이트. Hover 시 `ink`로 깊어진다. Disabled는 opacity 40%. 로딩 중 라벨은 "대조 중…".
- **반전 버튼 (네이비 밴드 위):** `band-hi` 배경 + `band` 글자, hover 시 순백(#FFFFFF). 구독대·판머리 compact 조회 버튼.
- **보조 버튼:** 투명 배경 + `ink-2` 1px 테두리 + `ink` 글자, hover 시 `paper` 배경.
- **인장 버튼 (인주 예약 사용처):** `injuk` 1px 테두리 + `injuk` 글자, hover `injuk-soft` 배경. 저장 상태는 `injuk-soft` 배경 + `injuk-deep` 글자, 라벨 "검토 인장 찍기" ↔ "검토 인장 해제", `aria-pressed` 사용.
- **텍스트 액션:** "조건 해제" 등은 밑줄(underline-offset 2px) + `ink` 700. 랜딩 피처 행 CTA는 `band` 글자 + hover 밑줄.

### Chips
- **시그널·증거 칩 (정보 표시):** 3px 직사각형, 12px 600. 긍정 시그널·증거 = `tint` 배경 + `tint-line` 테두리 + `tint-ink` 글자. 감점 시그널 = `paper` 배경 + `rule` 테두리 + `ink-3` 글자 + 앞머리 "−". 중립 = `sheet` 배경.
- **필터 캡슐 (컨트롤):** 캡슐형, h 28px, 12.5px 600, `aria-pressed`. 비활성 = `sheet` 배경 + `rule` 테두리. 활성 = `ink` 배경 + `paper` 글자 + 앞머리 6px 점(일반 필터는 틴트 점, "검토 인장" 필터만 인주 점).

### Cards / Containers
카드는 없다. 컨테이너는 색 밴드(네이비/장부지)와 괘선 구획뿐이다. 개봉면(행 내부 패널)은 `sheet` 배경 + 상단 dashed `tint-line` 절취선, 내부 패딩 16~24px.

### Inputs / Fields
- **지면 위 조회 (랜딩·본문):** 배경 없는 밑줄 입력 — 2px `ink` 밑줄, 포커스 시 유지·강조. 플레이스홀더 `ink-3` 400.
- **밴드 위 조회 (판머리 compact):** `band-ink` 1px 밑줄 + `band-hi` 글자 + `band-hi` 캐럿, 포커스 시 밑줄이 순백으로.
- **박스형 (textarea·이메일):** `sheet` 배경 + `rule`(밴드 위에서는 `tint-line`) 1px 테두리 + 3px 라운드, 포커스 시 테두리가 `ink`로. 글로우·링 없음.
- **전역 포커스:** `.world-gc :focus-visible` = 2px `ink` 실선 아웃라인, offset 2px, radius 2px. (미이관 표면의 전역 폴백은 3px 네이비 40% 아웃라인.)

### Navigation
- **Header:** `.world-gc` 적용, 스티키, `paper` 배경 + 이중 괘선(상단) + 하단 2px 잉크 괘선. 로고 "조달핏"은 명조 900 21px + 산세리프 태그라인 "공공입찰 검토 우선순위". 메뉴는 13.5px 700, 활성 = `ink` 글자 + 2px `band` 밑줄, hover = `rule` 밑줄. 모바일 메뉴는 `gc-open-wrap` 개봉 문법을 재사용한다.

### 개찰판 행 (시그니처 컴포넌트)
행 전체가 개봉 토글 버튼이다(`aria-expanded`/`aria-controls`).
- **닫힘 (봉인):** 공유 괘선 위 1줄 — 순번·공고명(truncate)·마감·추정가·적합. 우측 하단 괘선 위에 네이비 **봉인 딱지**가 걸쳐 있고, 우측 끝 셰브론이 개봉 가능함을 알린다. Hover 시 `sheet/60` 배경.
- **개봉:** 배경이 `sheet`로 바뀌고 딱지가 사라지며, dashed 절취선 아래 개봉면이 열린다 — 추천 근거(LLM), 시그널·증거 칩, ※ 자격 확인·투찰 가능 업종 각주, 액션 줄(인장 버튼 / 상세 분석 / 나라장터 원문 + 공고번호). 첫 행은 개봉된 채로 도착한다 — 판의 첫인상이 곧 근거다.
- **저장 (인장):** 순번 위에 원형 "검토" 인주 스탬프가 -4°로 안착. localStorage(`jf_shortlist_v1`) 기반, 회원가입 없음.
- **마감 표기:** D≤2 인주 700 / D3~5 앰버 700 / D6~60 잉크 / 60일 초과는 날짜로 강등 / 지난 건 "마감" muted.
- **적합 표기:** 라벨(매우 적합 ≥0.85 / 적합 ≥0.7 / 관련 있음 ≥0.55 / 참고) + % 숫자 병기. 상위 2단계만 `ink`, 나머지는 `ink-3`.

### 판머리 (BoardHead)
네이비 밴드가 소유하는 첫 화면 — 명조 900 `band-hi` 대활자 제호 + "검토 우선순위 N건" 병기, `band-ink` 메타(마스킹 사업자번호·지역·구분)와 "{날짜} 조회 · 매일 갱신 · 나라장터 기반" 출처 줄, 우측에 흰 지면 판 위 관인(62px)과 compact 조회 폼.

### 데이터 시각화
차트는 네이비 순차 램프 5단(#1E3A66, #3D5F94, #7591BD, #AEBFDA, #DBE4F1)을 쓴다. 아이덴티티 래스터(파비콘 icon.svg, OG 이미지)의 PRIMARY도 #1E3A66 — 화면과 래스터가 같은 축이다.

### 모션 문법 (컴포넌트 귀속)
- **개봉:** `grid-template-rows 0fr → 1fr`, 0.45s `cubic-bezier(0.16, 1, 0.3, 1)` (`.gc-open-wrap`). 셰브론은 0.3s 회전.
- **인장 안착:** `gc-stamp` 0.3s `cubic-bezier(0.2, 0.8, 0.3, 1)` — scale 1.4 → 0.98 → 1, -8° → -4°로 절제되게 내려앉는다.
- **대조 중 (로딩):** 1px 괘선 트랙 위를 잉크 바가 훑는 `gc-scan` 1.6s 무한 스캔 + "보통 5~12초 소요됩니다" 안내.
- **reduced-motion:** 세 가지 모두 `prefers-reduced-motion: reduce`에서 완전히 꺼진다.
- 그 외 상태 전환은 `transition-colors` 150ms 수준의 무채색 전환뿐 — 바운스·패럴랙스 없음. 랜딩 히어로만 `rise`(0.5s translateY 8px, 지연 스태거) 등장을 쓴다.

### 브라우저 표면
`.world-gc`가 브라우저 기본 표면까지 세계로 물들인다: 텍스트 선택 = 청색 틴트 `rgba(185,201,224,0.45)`(전 사이트 공통), 캐럿 = `ink`(밴드 위에서는 `band-hi`), 스크롤바 = `tint-line`/`paper` (`scrollbar-color`).

## Do's and Don'ts

### Do:
- **Do** 새 표면·리디자인 표면은 루트에 `.world-gc`를 적용하고 이 문서의 gc 토큰만 사용한다.
- **Do** 목록은 번호 행 + 공유 괘선으로 짠다 — 순번 zero-pad 2자리, 수치 컬럼 우측 정렬, 전 수치 tabular.
- **Do** 장부지 위 섹션 머리는 명조 900 + 이중 괘선(`.gc-double-rule`) 조합으로 열고, 네이비 밴드는 괘선 없이 면으로 세운다.
- **Do** 면책·주석은 "※ " 접두(마커는 `aria-hidden`) + `ink-3` 12~12.5px 각주로 쓴다.
- **Do** 데이터 출처를 상시 명시한다 — "{날짜} 조회 · 매일 갱신 · 나라장터 기반", 사업자번호는 "137-XX-X4567" 마스킹.
- **Do** 서술형 카피는 합니다체("대조하고 있습니다", "냅니다")로 쓴다. 권유형 "-세요"까지는 허용.
- **Do** 개봉·안착·스캔 모션에는 반드시 reduced-motion 해제를 함께 둔다.
- **Do** 차트·래스터에는 네이비 순차 램프와 PRIMARY #1E3A66을 쓴다 — 화면과 산출물이 같은 축이어야 한다.

### Don't:
- **Don't** 카드 그리드·box-shadow·큰 라운드(3px 초과, 캡슐 컨트롤·배지 제외)를 쓰지 않는다 — SaaS 대시보드 문법은 이 세계의 안티테제다. 레거시 유틸(`.card-soft`, `.btn-primary`, `--shadow-*`)은 미이관 표면의 잔여물이며 새 표면에 들이지 않는다.
- **Don't** 인주를 예약 사용처(마감 D≤2, 인장·관인) 밖에서 쓰지 않는다 — 화면에서 유일한 붉은 사건. 일반 강조·링크·버튼에 붉은색 금지.
- **Don't** 인주 획을 어두운 배경에 직접 올리지 않는다 — 도장은 항상 종이(흰 지면 판) 위에 찍는다.
- **Don't** "낙찰 가능성 X%"·"따낼 만한" 카피 금지 — 항상 "검토 우선순위"·"검토할 만한" + "적합도는 검토 우선순위이며 낙찰 가능성이 아닙니다" 면책.
- **Don't** 명조를 본문·컨트롤에 쓰거나 900 외의 웨이트로 쓰지 않는다.
- **Don't** 장식 이모지·글리프 장식·장난스러운 톤을 넣지 않는다. 아이콘은 기능적 스트로크 아이콘(셰브론, 외부 링크 화살표) 최소한으로.
- **Don't** 없는 증거(후기·도입 사례·언론 보도)를 만들지 않는다 — 예시 데이터에는 "예시 데이터로 표시 중입니다" 각주를 단다.
