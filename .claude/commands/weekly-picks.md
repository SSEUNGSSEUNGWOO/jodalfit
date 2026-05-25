---
description: 이번 주 검토할 만한 공고 TOP 10 큐레이션 발행. writer(claude) → evaluator(codex) → proofreader(claude) → 마크다운 저장
---

이번 주 picks 인사이트를 발행한다.

## 실행

```
cd backend && uv run python -m jobs.weekly_insight.cli --type picks
```

- 인자 없으면 오늘 기준 ISO 주차 (월요일 ~ 일요일).
- 지난 주를 발행하려면: `--year-week 2026-w21`
- 출력: `frontend/src/content/insights/picks/{slug}.md`

## 워크플로우

1. Supabase에서 해당 주 신규 공고 fetch + dedupe
2. 룰 기반 선별 (추정가 1억+, 마감 미래, 민간 발주 제외, 같은 기관·사업 중복 제거) → 10건
3. **Writer (Claude CLI)** 가 10건에 12~25자 blurb 한 번에 JSON으로 생성
4. **Evaluator (Codex CLI)** 가 rubric.yaml 기준 평가
   - factual_accuracy / concrete / tone / relevance / format
   - 가중 점수 4.0 미만 또는 항목 3점 미달 시 피드백 → Writer 재시도 (최대 2회)
5. 통과 후 **Proofreader (Claude CLI)** 가 오타/문장부호/한자 교정
6. 마크다운 저장 + 페이지는 `/insights/picks/{slug}`에서 자동 노출

## 주의

- ANTHROPIC_API_KEY 사용 금지 (구독 모델). 잡 내부에서 env 제거함
- 같은 주차 재실행 시 파일 덮어쓰기
- 발행 후 한 번 더 사람 눈으로 확인 권장
