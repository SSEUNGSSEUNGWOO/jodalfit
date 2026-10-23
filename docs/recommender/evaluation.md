# 추천 평가 하네스 (채점표)

실행: `cd backend && uv run python -m jobs.evaluate_recommender --as-of YYYY-MM-DD --companies 300 [--seed 7 --pool 200 --limit 30 --run-id NAME]`
결과: `backend/data/recommender_eval/<run_id>/` (manifest.json / metrics.json / report.md / failures.csv). gitignore 대상이라 기준점은 이 폴더에 report.md 를 복사해 둔다.
코드: `backend/jobs/evaluate_recommender.py`(DB 추출·재생·보고서), `backend/app/recommender/evaluation.py`(지표 순수 함수, `uv run python -m app.recommender.evaluation` 으로 self-check).

## 규칙
- 정답 = `award_results.is_winner` 인 공고 중, t 에 활성(게시 < t, t+2일 ≤ 마감 ≤ t+90일)이었던 것. 마감 1일 이내 공고는 t 시점에 발견할 수 없는(이미 입찰 중인) 공고라 제외 — 운영의 '마감 임박 −30' 과 같은 기준(2026-10-14, 9/1 정답의 35%가 이 경우였다). 미낙찰·미참가는 음성이 아님.
- 회사 벡터·거래기관·금액 중간값·기관 통계는 **t 이전 데이터로 재합성**. 정답 공고와 같은 공고번호는 이력에서 제거(누수 차단).
- 회사 표본 = 정답이 있는 회사 중 cold(이력 0) / small(1~5) / rich(6+) 각 100곳, seed 고정. 이력 건수는 계약 1.0 + 참가 0.4 가중.
- 후보 집합 = t 에 활성이고 임베딩 있는 공고 전부 (운영 RPC 조건과 동일). dense 는 정확 코사인.
- 파이프라인은 운영 함수(`score_notice`, `check_qualifications`, `mmr_diversify`) 를 그대로 import. DB 는 읽기 전용 세션.
- 지표: dense@pool(dedup 후), qual@pool(자격 후), scored@30(MMR 전), final@30, MRR. 회사 macro 평균 + 정답 가중 micro. 군: cold/small/rich, 업무구분.
- 운영 프론트(결과 페이지)는 **pool 200 / limit 20** 을 요청한다(2026-10-23 결정 — K 곡선과 실사용 로그 근거는 changelog 참조). final@30 은 파이프라인 상한이고, 사용자 체감은 --limit 20 으로 잰다(limit=30 에서는 MMR 손실이 구조적으로 거의 측정되지 않는다).
- `--limit 30` 으로 돌리면 보고서에 **K 곡선**(final@3·5·8·12·16·20·25·30)이 같이 나온다. 몇 건을 보여줄지 다시 논할 때 쓴다.
- 손실 단계(failures.csv `lost_at`): dense = dense 상위 pool×2 밖 · dedup = 후보 풀 pool 컷(지문 중복 제거 포함) · qualified = 자격 하드 제외 · scored = 점수 순위 limit 밖 · final = MMR 에 밀림.
- 한계: 업종·물품·지역은 현재 값. 낙찰 라벨은 기존 거래처 편향. "낙찰 확률"이 아니라 "검토할 공고를 놓치지 않는가"를 잰다.
- 운영과 알려진 차이: 회사 업종·물품은 같은 사업자번호의 모든 행 합침(운영은 한 행). 참가 이력 시점은 개찰일 기준. 게시일 = t 공고 제외. 정답·순위 비교는 공고번호 단위(차수 무시). 기관 통계는 t 이전 2년 계약.
- 후보 검색 방식은 --retrieval (기본값 = 운영 설정 RECO_RETRIEVAL). 운영 변경 전후 비교는 --retrieval dense / hybrid 로 명시한다.

## 변경 비교 방법
같은 `--as-of --seed --companies` 로 전후 실행 → `metrics.json` 의 macro·군별 차이를 본다. 한 군이 떨어지면 전체 평균이 올라도 채택하지 않는다. 두 시점(8/1, 9/1)에서 같은 방향이어야 한다.

2026-10-16 부터 모든 알고리즘 실험은 `--companies 3000 --seed 7` 로 전후 비교한다 (세 시점 7/1·8/1·9/1, 기준점 `baseline-2026-10-16-big.md`). 300곳에서는 회사 한두 곳이 지표를 0.01 움직여 잡음과 구분이 안 됐다 — 예: 0049 자격등록 마감 제외가 300곳 7/1 에서 small −0.01, 1,582곳에서는 모든 군 +.
정답·표본은 현재 DB 내용에 의존한다(과거 t 의 낙찰 데이터가 나중에 추가됨) → 전후 비교는 연속 실행에서만 유효하다.

## Baseline
`baseline-2026-08-01.md`, `baseline-2026-09-01.md`(pool 200 / limit 30, 파이프라인 상한), `baseline-2026-08-01-top5.md`(pool 100 / limit 5, 운영 프론트 조건 = 사용자 체감) 참조. 코드 d9596b6 기준.
