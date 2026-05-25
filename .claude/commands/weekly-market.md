---
description: 이번 주 공공조달 시장 동향 리포트 발행. writer(claude) → evaluator(codex) → proofreader(claude) → 마크다운 저장
---

이번 주 market 인사이트를 발행한다.

## 실행

```
cd backend && uv run python -m jobs.weekly_insight.cli --type market
```

- 인자 없으면 오늘 기준 ISO 주차 (월요일 ~ 일요일).
- 지난 주를 발행하려면: `--year-week 2026-w21`
- 출력: `frontend/src/content/insights/market/{slug}.md`

## 워크플로우

1. Supabase에서 해당 주 + 직전 주 신규 공고 fetch + dedupe
2. 룰 기반 통계 (업무구분 분포 / TOP 발주기관 / 예산 버킷 / 평균·중간값 / w/w)
   - 전주 표본이 200건 미만이면 w/w 생략
   - "각 수요기관" 같은 정규화 안 된 값 자동 필터
3. **Writer (Claude CLI)** 가 통계를 받아 3~5문장 한국어 한 단락 narrative 생성
4. **Evaluator (Codex CLI)** 가 rubric.yaml 기준 평가
   - 일반론 ("활발한 동향", "반영하고 있다") 자동 감점
   - 표 수치 단순 나열 → concrete 감점
   - 가중 점수 4.0 미만 또는 항목 3점 미달 시 피드백 → Writer 재시도 (최대 2회)
5. 통과 후 **Proofreader (Claude CLI)** 가 교정
6. 마크다운 저장 + 페이지는 `/insights/market/{slug}`에서 자동 노출

## 주의

- ANTHROPIC_API_KEY 사용 금지 (구독 모델)
- 같은 주차 재실행 시 파일 덮어쓰기
- narrative는 표 데이터와 일치해야 함. evaluator가 표·narrative 정합성 검증
