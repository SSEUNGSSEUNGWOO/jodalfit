# 조달핏 일일 마케팅 성적표

매일 아침 `/marketing-report` 한 번이면 어제(KST) 성적표가 `docs/marketing/reports/YYYY-MM-DD.md`로 나온다.
숫자는 전부 코드가 만들고, LLM은 마지막에 표만 읽고 300자 해석을 쓴다.

```
cd backend
uv run python -m jobs.marketing_report.cli                 # 어제
uv run python -m jobs.marketing_report.cli --date 2026-09-17
uv run python -m jobs.marketing_report.cli --skip naver     # 소스 건너뛰기 (gsc, naver, supabase)
uv run python -m jobs.marketing_report.cli --no-interpret  # LLM 해석 생략
```

소스 하나가 실패해도 나머지로 성적표를 내고, 사유는 맨 아래 "수집 상태" 표에 남는다.
스냅샷(`docs/marketing/snapshots/YYYY-MM-DD.json`)은 전주·전일 비교의 원천이라 리포트와 함께 커밋한다.

## 여섯 칸

| 칸 | 무엇을 | 어디서 | 비교 기준 |
|---|---|---|---|
| 1. 색인·크롤 (구글) | 사이트맵 표본 100개(회사 50·공고 50, 매일 같은 URL)의 색인 비율, 사이트맵 제출·색인 수 | 서치콘솔 URL 검사 API, Sitemaps API | 전주 같은 요일 |
| 2. 구글 검색 유입 | 클릭·노출·CTR·순위, 페이지 유형별(회사/공고/업종/인사이트), 상위 검색어 10 | 서치콘솔 Search Analytics | 전주 같은 요일 |
| 3. 네이버 서치어드바이저 | 일별 클릭·노출·CTR, 색인·수집제한·색인제외, 수집 페이지·오류, 페이지 유형별, 상위 검색어 | 로그인 세션으로 콘솔 내부 API 호출 (공식 API 없음) | 전주 같은 요일 |
| 4. 사람 행동 | SSR 제외 실제 검색, 회사 식별 성공, **재검색율**, 공고 클릭·저장, 구독·이메일 | Supabase RPC `marketing_daily_stats` (0033) | 전주 같은 요일 |
| 5. 제품 건강 | 오류율, 결과 0건 비율, p50 응답 | 같은 RPC | 전주 같은 요일 |
| 6. 키워드 추적 | 33개 키워드의 네이버·구글 순위 상승·하락·신규·이탈 | 네이버 상위 검색어, 서치콘솔 query (정확 일치) | 직전 스냅샷 |

- 성공 기준은 신규 유입이 아니라 **재검색율** — 그날 사람이 검색한 회사 중 직전 7일 안에도 검색됐던 회사의 비율.
- 구글 색인이 풀리기 전(발견됨-미색인 6만 건)엔 1번 칸의 표본 색인 비율이 첫 지표다. 서치콘솔 데이터는 1~2일 늦게 확정돼서 어제가 비면 최대 3일 물러나고, 표에 기준일을 적는다.
- 키워드 목록과 랜딩·근거는 `backend/jobs/marketing_report/config.yaml`. 공고명 3개는 마감되면 이탈하니 주 1회 `/notices`에서 교체.

## 최초 설정

### 서치콘솔 (설정 완료)
`agent-pipeline/pipelines/seo`와 같은 서비스 계정 키 `~/.claude/marketing/gsc-key.json`(seo-pipeline@…)을 그대로 쓴다.
찾는 순서는 환경변수 `GSC_KEY_PATH` → `~/.claude/marketing/gsc-key.json` → `backend/secrets/gsc-service-account.json`.
이 계정은 서치콘솔 `jodalfit.co.kr` 속성에 이미 사용자로 등록돼 있어 검색 데이터·사이트맵·URL 검사가 모두 된다 (2026-09-18 확인).
새 키를 만들 일이 생기면: Google Cloud → Search Console API 사용 설정 → 서비스 계정 키(JSON) → 서치콘솔 속성 사용자에 계정 이메일 추가.

URL 검사 API 한도는 하루 2,000건·분당 600건. 표본 100개라 한도는 여유 있지만 순차 호출이라 수 분 걸린다.

### 네이버 (한 번 + 만료 시)
1. 이 세션 프롬프트에 `! cd C:\dev\personal\jodalfitbackend; uv run python -m jobs.marketing_report.cli --naver-login`
   → 뜬 창에서 네이버 로그인(**로그인 상태 유지** 체크) → 서치어드바이저 화면이 보이면 창 닫기.
   프로필은 `backend/data/naver-profile`(gitignored). 2026-09-18 설정 완료.
2. 매일 headless 로 사이트 요약 화면을 열어 세션을 살리고, 화면이 쓰는 콘솔 내부 API 를 같은 세션으로 직접 부른다.
   원본 응답은 `backend/data/naver/YYYY-MM-DD/*.json`. 세션이 만료되면 수집 상태에 "로그인 세션 만료"가 찍히니 1번을 다시.

네이버 칸에 나오는 것 (엔드포인트와 필드는 `naver.py` 상단 주석):
- 일별 클릭·노출·CTR — 성적표 날짜와 정확히 같은 날.
- 색인 페이지·수집제한·색인제외 — "사이트 진단" 기준. 네이버 진단은 1~2일 늦게 갱신돼서 표에 진단 날짜를 붙인다.
- 수집 페이지·수집 오류 — "수집 현황" 기준 일별.
- 페이지 유형별 클릭·노출, 상위 검색어 — 최신일 클릭 상위 URL·검색어 50개 기준 (전체 합계가 아님).
- 키워드 추적 — 위 상위 검색어 50개 안에 든 추적 키워드의 순위. 50개 밖이면 "노출 없음"으로 잡힌다.

### 해석기
`claude -p`(구독 CLI)를 쓴다. ANTHROPIC_API_KEY는 쓰지 않는다. 300자 안팎, 표에 없는 숫자는 못 쓰게 프롬프트에 박혀 있다.

## 다음 단계 (아직 안 함)
- GA4: 채널 귀속(구글·네이버·뉴스레터 중 어디서 왔나)이 필요해지면 gtag 삽입 후 7번 칸 추가.
- 어드민 그래프·자동 발행은 `snapshots/*.json`을 그대로 데이터 소스로 쓰면 된다.
