---
description: 어제 마케팅 성적표 발행 — 서치콘솔·네이버·Supabase 수집 → 전주 비교표 → claude 300자 해석 → docs/marketing/reports/YYYY-MM-DD.md
---

어제(KST) 조달핏 마케팅 성적표를 만든다. 설명서는 docs/marketing/README.md.

## 실행

```
cd backend && uv run python -m jobs.marketing_report.cli $ARGUMENTS
```

- 인자 없으면 어제. 특정 날짜는 `--date 2026-09-17`. 소스 제외는 `--skip naver,gsc`.
- 끝나면 `docs/marketing/reports/<날짜>.md`를 읽고 **"한 줄 해석"과 수집 상태 표를 그대로 보여준다.** 숫자를 새로 해석하거나 바꾸지 않는다.
- 수집 상태에 실패가 있으면 README의 해당 설정 항목(서치콘솔 키 / 네이버 로그인)을 한 줄로 안내한다. 네이버 "로그인 세션 만료"면 `--naver-login` 재실행을 안내한다.
- 리포트와 스냅샷(`docs/marketing/snapshots/`)은 커밋 대상이다. 커밋은 사용자가 시키면 한다.

## 주의

- 숫자는 코드가 만든다. LLM 해석은 표만 읽는다.
- ANTHROPIC_API_KEY 사용 금지 (구독 CLI).
