# 추천 알고리즘 코드 리뷰 (Codex, 2026-10-13)

질문: `C:/dev/ops/jodalfit/design/codex_prompt2.md`. 코드 실제 열람 기반, 파일 변경 없음.

승우님, **우선순위는 `평가 하네스 → 자격·회사 식별 정합성 → 하이브리드 후보 검색 → 다중 벡터 → 점수 조정`입니다. KURE-v1 교체는 그 뒤가 맞습니다.** 후보에서 빠진 공고는 점수나 MMR로 복구할 수 없고, 현재 회사 벡터를 그대로 쓰는 낙찰 held-out 평가는 정답 누수로 성능을 과대평가합니다.

지정한 코드·마이그레이션·문서를 실제로 읽었습니다. 아래는 코드 리뷰와 수정 설계이며, 파일 변경이나 운영 DB 측정은 하지 않았습니다. 성능 수치는 코드 주석에 기록된 과거 측정과 앞으로 검증할 목표를 구분했습니다.

**먼저 현재 흐름을 바로잡아야 합니다.**

| 항목 | 실제 코드 |
|---|---|
| API 기본값 | v2, 후보 200, 결과 20. `recommend.py` 직접 호출 기본값은 v1, 후보 100, 결과 5 |
| 검색량 | RPC에서 `candidate_pool × 2` 조회 → 중복 제거 → `candidate_pool`로 절단 |
| 자격 검사 | 후보 절단 **뒤에** 하드 제외 |
| 유사 회사 기관 +30 | 점수 함수에는 있지만, 파이프라인에서는 비활성화 |
| MMR | 점수 상위 40개에서 **첫 5개만** 다양화, 나머지는 기존 점수순 |
| dense 검색 | 활성 공고를 `MATERIALIZED` CTE로 모은 뒤 **정확 코사인 정렬** |

근거: [API 기본값](/C:/Dev/personal/jodalfit/backend/app/api/recommendations.py:55), [후보 검색](/C:/Dev/personal/jodalfit/backend/app/services/recommend.py:445), [v2 파이프라인](/C:/Dev/personal/jodalfit/backend/app/recommender/pipeline.py:59), [현재 RPC 정의](/C:/Dev/personal/jodalfit/supabase/migrations/0018_match_bid_notices_max_horizon.sql:47).

---

**1. 심각도 순으로 본 결함·비효율**

여기서 P1은 추천 누락·오판 또는 평가를 무효화하는 문제, P2는 순위 품질·응답 지연 문제, P3는 유지보수·표현 문제입니다.

| 심각도 | 파일·함수·줄 | 발견 내용과 영향 |
|---|---|---|
| **P1** | `recommend.py::_search_with_embedding` **445–489**, `pipeline.py::rank_v2` **41–57** | 자격 검사 전에 후보 수를 절단합니다. 가까운 부적격 공고가 후보를 차지하면, 그 아래 적격 공고는 랭커에 도달하지 못합니다. RPC를 2배로 조회해도 자격 검사 전에 다시 절단하므로 해결되지 않습니다. |
| **P1** | `qualifications.py::check_qualifications` **33–45, 61–72** | 면허는 이름·괄호 앞 이름의 교집합, 지역은 시도 또는 문자열 포함으로 판단합니다. 코드·유효기간·상태를 사용하지 않습니다. 세부 업종을 괄호 제거로 같은 자격으로 취급하거나 시군구 제한을 시도 단위로 통과시킬 위험이 있습니다. **실제 오류율은 표본 확인 필요**입니다. |
| **P1** | `recommend.py::_fetch_company_terms` **546–569**, `compute_company_vectors.py::process_chunk` **302–309** | 회사 벡터는 같은 정규화 사업자번호의 여러 회사 행을 합치지만, 온라인 업종 조회는 선택된 `bizrno` 한 행만 읽습니다. 하이픈 행에만 붙은 업종이 누락되면 잘못 제외되거나 확인불가로 통과합니다. |
| **P1** | `pipeline.py::rank_v2` **47–50**, `qualifications.py::check_qualifications` **25–29, 55–59** | 제한 행이 없으면 “제한 없음”입니다. 하지만 제한 수집 실패·미수집과 실제 무제한을 구분할 상태가 없습니다. 회사 정보 부재는 `unverified`지만 공고 제한정보 부재는 검증된 무제한처럼 표시됩니다. |
| **P1 — 평가** | `compute_company_vectors.py::process_chunk` **362–428**, `recommend.py::_fetch_company_history` **754–772**, `0038...sql` **13–20** | 회사 벡터·회사 거래기관·기관 통계가 현재 전체 데이터로 만들어집니다. 이 상태로 과거 낙찰을 숨겨 평가하면 해당 정답 및 이후 거래가 입력에 남습니다. 현재 운영의 버그라기보다 **앞으로 평가를 만들 때 반드시 해결할 문제**입니다. |
| **P2** | `compute_company_vectors.py::build_industry_text` **273–283**, `process_chunk` **430–440, 499–502** | 대표 업종을 중복 강조하고 업종·물품 각각 첫 10개만 넣으며, 수주·참가 공고는 평균 한 개로 합칩니다. 다분야 회사의 소수 분야가 희석됩니다. DB 조회에 명시적 정렬이 없어 어떤 항목이 첫 10개인지도 안정적으로 보장되지 않습니다. |
| **P2** | `compute_company_vectors.py::process_chunk` **413–428** | 계약·참가 건수를 임베딩 존재 확인 **전에** 늘립니다. 임베딩 없는 이력까지 가중치 티어에 영향을 줍니다. 같은 공고의 계약 변경차수·복수 계약도 그대로 평균에 들어가므로 특정 공고가 과대표집될 수 있습니다. 중복 규모는 확인 필요입니다. |
| **P2** | 같은 파일 **440, 484–502** | 수주 평균 벡터를 정규화하지 않고 단위 업종 벡터와 합칩니다. 최종 벡터만 정규화합니다. 따라서 실제 수주 영향은 설정 가중치뿐 아니라 **수주 평균의 노름**, 즉 이력의 응집도에 달려 있습니다. 의도라면 문서화해야 하고, 아니라면 비교 실험이 필요합니다. |
| **P2** | `recommend.py::_search_with_embedding` **466–485** | 같은 공고번호의 차수는 최신본이 아니라 **유사도가 가장 높은 본**이 살아남습니다. 정정으로 자격·마감이 달라졌다면 옛 차수의 조건으로 추천할 수 있습니다. 제목·기관·마감·가격으로 서로 다른 번호도 제거하므로 별개 발주를 합칠 위험도 있습니다. |
| **P2** | `score.py::score_notice` **35–83** | 거래기관 +50, 지역 +30 등은 유사도 차이를 크게 압도할 수 있습니다. 예를 들어 유사도 0.55의 기존 기관 공고가 0.90의 신규 기관 공고보다 먼저 올 수 있습니다. 이것이 나쁜지는 평가해야 하지만, 현재 가중치를 정당화할 측정 근거는 없습니다. |
| **P2** | `score.py` **46–54**, `0038...sql` **15–16** | `1 - distinct_winners / total`은 “고정 거래처 경향”의 충분한 지표가 아닙니다. 100건을 50개 회사가 2건씩 받은 기관도 0.5입니다. 계약 변경차수·반복 계약이 있으면 더 부풀 수 있습니다. 자기 회사가 기존 거래처여도 +50과 −20이 함께 붙습니다. |
| **P2** | `recommend.py::_fetch_company_history` **754–772** | 정렬 없이 500건으로 제한합니다. 최신 이력이라는 보장이 없고 기간도 없습니다. 짝수 개 금액의 중간값은 두 중앙값의 평균이 아니라 위쪽 중앙값입니다. 계약액과 공고 추정가격의 기준 차이도 검토해야 합니다. |
| **P2 — 지연** | `collaborative.py::fetch_institution_stats` **71–94**, `recommend.py::_rpc_with_retry` **53–68** | 캐시 통계 실패 시 무거운 원래 집계로 돌아가고, RPC timeout 후 다시 호출합니다. 주석상 과거 원래 집계는 4–6초였습니다. 캐시 장애 시 1초 목표를 크게 초과할 수 있습니다. |
| **P2 — 지연** | `recommend.py::_recommend_auto` **831–833**, `_recommend_by_keywords` **868–872**, `_recommend_by_company` **937–948** | auto는 회사·키워드 경로를 직렬 실행하고, 키워드 경로의 세 검색도 직렬입니다. 벡터 미보유·키워드 추가 시 요청 중 외부 임베딩 API도 호출합니다. 회사 벡터 검색만 빨라져도 모든 모드의 1초를 보장하지는 못합니다. |
| **P3** | `mmr.py::mmr_diversify` **31–51**, `pipeline.py` **100–108** | 후보 집합의 min–max로 점수를 정규화하므로 같은 점수 차이가 요청마다 다른 의미가 됩니다. 임베딩 누락 후보는 중복 패널티를 받지 않습니다. 현재는 TOP 30 전체의 다양화가 아닙니다. |
| **P3** | `embed_bid_notices.py::fetch_pending` **73–82** | 기본 재임베딩 조건은 `embedded_at IS NULL`뿐입니다. 원문 변경을 임베딩 갱신과 연결하는 해시가 없습니다. **수집 잡이 변경 때 이를 초기화하는지는 추가 확인 필요**입니다. |
| **P3** | `README.md` **85–93, 140**, `CLAUDE.md` **34–36** | 문서는 자격 선필터·협업 시그널을 설명하지만 실제 흐름과 다릅니다. README의 회사 입력 필드도 현재 잡과 일부 다릅니다. 성능 실험 전에 실행 버전과 문서를 맞춰야 합니다. |

주요 코드 링크: [qualifications.py](/C:/Dev/personal/jodalfit/backend/app/recommender/qualifications.py:11), [회사 벡터 합성](/C:/Dev/personal/jodalfit/backend/jobs/compute_company_vectors.py:287), [score.py](/C:/Dev/personal/jodalfit/backend/app/recommender/score.py:22), [MMR](/C:/Dev/personal/jodalfit/backend/app/recommender/mmr.py:18), [통계 폴백](/C:/Dev/personal/jodalfit/backend/app/recommender/collaborative.py:59), [공고 텍스트](/C:/Dev/personal/jodalfit/backend/jobs/embed_bid_notices.py:32).

**반대로 지금 잘 선택한 부분도 있습니다.** 활성 약 1만 건을 먼저 제한하고 정확 정렬하는 RPC는 현재 규모에 합리적입니다. 이를 “ANN 인덱스를 안 타니 결함”으로 보지 않겠습니다. [0016 마이그레이션 3–7줄](/C:/Dev/personal/jodalfit/supabase/migrations/0016_match_rpc_iterative_scan.sql:3)은 이 경로가 과거 약 100ms였다고 기록합니다. 현재 성능은 재측정해야 합니다.

---

**2. 1단계: 과거 낙찰 held-out 평가 하네스**

**정답 라벨이 전혀 없는 것은 아닙니다.** 낙찰·계약은 강한 양성 라벨이고, 참가 결과는 별도의 의도 라벨로 쓸 수 있습니다. 다만 미낙찰·미참가를 부적합 음성으로 취급하면 안 됩니다.

변경 파일 제안:

- 신규 `backend/jobs/evaluate_recommender.py`: 데이터 추출, 시간 분할, 지표·실패 사례 출력.
- 신규 `backend/app/recommender/evaluation.py`: 순수 지표 계산.
- `compute_company_vectors.py`: 벡터 합성 부분에 `as_of`와 입력 이력을 전달할 수 있게 최소 분리.
- `pipeline.py`: `today`와 미리 계산한 기관 통계를 주입할 수 있게 변경.
- `docs/recommender-evaluation.md`: 데이터 범위·누수 제한·실험 규칙.
- 산출물은 `backend/data/recommender_eval/<run_id>/`에 manifest, 지표, 실패 사례 저장.

테스트 프레임워크를 먼저 도입할 필요는 없습니다. 기존 CLI 스타일로 `uv run python -m jobs.evaluate_recommender ...`를 만들고, 지표 계산·시간 경계에 작은 assertion 검증을 붙이면 됩니다.

**A. 양성 라벨 만들기**

기본 단위는 다음입니다.

```text
(company_bizrno_norm, bid_ntce_no, bid_ntce_ord)
```

1. `award_results.is_winner = true`를 정규화 사업자번호로 묶습니다.
2. `contracts.rprsnt_corp_bizrno_norm`과 공고 복합키로 연결해 계약 확인 여부를 붙입니다.
3. 계약은 변경차수·복수 계약으로 양성을 여러 번 세지 않도록 회사–공고 단위로 중복 제거합니다.
4. 계약만 있는 양성도 별도 출처로 포함하되 공고번호·차수 누락, 공고 미연결, 두 출처 충돌은 별도 집계합니다.
5. 차수가 안 맞는다고 공고번호만으로 무조건 연결하지 않습니다. 먼저 수집값과 실제 변경 관계를 확인합니다.

스키마 근거: [contracts 63–88줄](/C:/Dev/personal/jodalfit/supabase/migrations/0001_init.sql:63), [award_results 308–322줄](/C:/Dev/personal/jodalfit/supabase/migrations/0001_init.sql:308), [정규화 컬럼](/C:/Dev/personal/jodalfit/supabase/migrations/0002_bizrno_normalize.sql:10).

라벨은 `winner_only`, `contract_confirmed`, `contract_only`로 나눠 같은 결과를 각각 보고합니다. 관측 가능한 날짜가 부족한 행은 시간 평가에서 제외하고 건수를 표시합니다.

**B. 시간 분할과 추천 상황 복원**

랜덤 낙찰 행 분할을 하지 않습니다. 데이터가 충분한 기간에서 이전 구간은 개발, 그다음 구간은 검증, 마지막 구간은 최종 테스트로 고정합니다. 구체 날짜는 DB의 날짜별 연결 가능한 양성 수를 확인한 뒤 정합니다.

일별 추천 시점 `t`마다 경쟁 후보는 다음입니다.

```text
bid_ntce_date < t
AND bid_clse_date >= t
AND bid_clse_date <= t + 90일
```

날짜만 있으므로 일 경계로 평가하고, 같은 날 공고는 제외하는 보수적 규칙을 사용합니다. 해당 시점에 활성이고 나중에 그 회사가 낙찰한 공고가 held-out 양성입니다.

**후보는 당시 활성 공고 전체입니다.** 양성에 몇 개 랜덤 공고만 섞으면 Recall@100이 실제 서비스보다 훨씬 쉬워집니다.

같은 공고가 여러 날 양성인 점을 고려해:

- 회사–일 단위 Recall을 계산하고,
- 회사별 평균을 낸 뒤 회사 평균을 계산하며,
- 회사–공고 단위 “활성 기간 중 한 번이라도 발견했는가”도 보조로 보고합니다.

목표 공고의 미래 낙찰 사실로 `t`를 고르지 않습니다. 고정된 일별 평가 일정에서 양성이 있는 회사–일을 평가합니다.

**C. 누수 방지 — 가장 중요한 부분**

| 입력 | 평가 규칙 |
|---|---|
| 회사 벡터 | 현재 `companies.embedding` 사용 금지. `t` 이전 이용 가능한 이력으로 재합성 |
| 계약 이력 | 계약일 `< t`. held-out 공고와 동일 공고번호의 모든 차수는 이력에서 제거 |
| 참가 이력 | 개찰 결과가 공개된 시점 `< t`. 단순 투찰 시각만으로 참가 결과를 미리 안 것으로 취급하지 않음 |
| 회사 거래기관·금액 | 같은 cutoff로 재계산. 현재 온라인 함수 호출 금지 |
| 기관 반복 통계 | 전체 회사의 계약에서 `< t` 조건으로 계산. 현재 MV 사용 금지 |
| 클러스터 | 평가 시점 이전 이력으로만 생성 |
| 점수·MMR | `date.today()` 대신 `t` 주입 |
| 정정·재공고 | 관련 공고가 train과 held-out 양쪽에 들어가 답을 노출하지 않는지 확인 |
| 캐시 | 운영 추천 캐시 사용 금지. 실험 설정·시점·입력 해시로 별도 캐시 |

`award_results.raw->>bidprcDt`는 현재 잡에서 읽지만, 이름만으로 **결과 공개 시각이라고 가정하면 안 됩니다**. `bid_notices.openg_date`와 raw 실제 필드를 대조하고, 판단 불가능한 참가 이력은 엄격 평가에서 제외합니다.

**현재 DB만으로 완전한 과거 운영 재현은 어렵습니다.** 회사 업종·지역의 과거 변경 이력과 공고 정정본의 당시 상태가 완전히 보존되었다는 근거가 없습니다. `created_at`도 과거 데이터를 나중에 백필한 적재 시각일 수 있습니다.

따라서 결과를 두 가지로 분리합니다.

- **시간 통제 평가:** 날짜가 확인되는 과거 이력만 사용. 회사 등록정보도 당시 존재를 확인할 수 있는 범위만 사용.
- **현재 등록정보 참고 평가:** 현재 업종·물품·지역을 고정해 후보 알고리즘을 비교. 과거 추천 성능으로 주장하지 않음.

앞으로는 일별 회사 프로필·공고 상태·검색 입력 버전을 저장해야 진짜 운영 재현 평가가 가능합니다.

**D. 반드시 보고할 지표**

```text
Recall@100 = |양성 ∩ 최종 후보 100| / |양성|
Recall@30  = |양성 ∩ 최종 결과 30| / |양성|
```

추가로:

- 자격 검사 전 후보 Recall@100.
- 자격 검사 후 후보 Recall@100.
- MMR 전·후 Recall@30.
- 후보 합집합 Recall: 각 검색 채널이 정답을 가져왔는지.
- 회사 macro 평균과 전체 양성 micro 평균.
- 최종 결과 30개 충족률, 확인불가 비율, 양성의 자격 오제외율.
- p50/p95/p99 응답시간과 RPC 시간, 캐시 hit/miss 분리.

회사 군은 **추천 시점 이전 정보**로 만듭니다.

| 군 | 기준 |
|---|---|
| 콜드스타트 | 과거 계약·참가 이력 0 |
| 소이력 / 풍부한 이력 | 중복 제거 이력 1–5 / 6+ |
| 단일 / 다분야 | 업종·물품 상위 분류와 과거 공고 분야 분산. 정확한 “부서” 라벨로 부르지 않음 |
| 데이터 완전 / 불완전 | 업종·지역·물품 확보 여부 |
| 업무구분 | 공사·용역·물품 |
| 지역 | 표본 충분한 지역만 비교 |

낙찰 라벨은 기존 거래처·성공 업체 편향이 있습니다. 그래서 낙찰 Recall만 최적화하지 말고 `award_results.is_winner = false`의 참가 공고 발견률을 별도로 확인하고, 실패·개선 사례를 수동 검토해야 합니다.

검증은 같은 평가 집합의 paired 비교로 합니다. 회사 단위 bootstrap 신뢰구간을 붙이고, 작은 회사 군의 상승·하락을 전체 평균에 숨기지 않습니다.

---

**3. 이후 수정은 작게 나눕니다**

| 단계 | 변경 파일 | 핵심 로직 | 검증 | 예상 효과 |
|---|---|---|---|---|
| **1. 평가 하네스** | 위 신규 CLI·평가 모듈, 벡터 잡·pipeline 최소 수정 | 시간 분할, 이력 재합성, 단계별 Recall | 누수 assertion, 연결률·군별 baseline | 이후 변경의 효과 판단 가능 |
| **2A. 회사 정합성** | `recommend.py` | 정규화 사업자번호의 모든 PK에 연결된 업종·물품 통합. 이름 trim·결정적 정렬 | 하이픈 중복 회사 표본, baseline 대비 오제외 | 벡터와 자격 입력 불일치 제거 |
| **2B. 자격 정합성** | `qualifications.py`, 제한 수집 잡, 신규 migration | 코드 기반 자격, 유효기간·상태, 지역 코드. `pass/fail/unknown` 구분 | 그룹 OR/AND·시군구·기간 경계 assertion, 과거 낙찰 오제외 수동 확인 | 잘못된 통과·제외 감소 |
| **2C. 후보 선필터** | 신규 RPC migration, `recommend.py`, `pipeline.py` | 확실한 자격 실패만 검색 전 제외. 공고 최신 유효 차수 선정 | Recall@100, 30개 충족률, SQL 실행계획 | 부적격 공고의 후보 점유 제거 |
| **3A. dense + 코드** | 검색용 테이블 잡·migration, 새 RPC | 코드 채널과 dense를 RRF로 결합 | 채널별 정답 유입, 후보 Recall@100 | 코드가 분명한 전문 분야 회수 |
| **3B. 문자 검색 추가** | 같은 RPC, `embed_bid_notices.py`의 텍스트 생성 부분 재사용 | FTS·trigram 채널 추가 | dense-only 대비 Recall, 실패 사례 | 고유 품목명·복합어 공고 회수 |
| **4. 다중 벡터** | `compute_company_vectors.py`, 다중 벡터 테이블·RPC, `recommend.py` | 업종 벡터 + 수주 클러스터 최대 3개 | 다분야 회사 Recall@100/@30, 지연 | 평균에 묻힌 분야 회수 |
| **5A. 이력·기관 점수** | `recommend.py`, `score.py`, 통계 잡·migration | 최근 중복 제거 이력, 정확한 median. 기관 보너스·개방성 항목 각각 ablation | Recall@30, 신규 기관 발견, 수동 적합성 | 검증된 순위 개선 |
| **5B. MMR 조정** | `mmr.py`, `pipeline.py` | 끄기/첫 5개/전체 30개 비교. 누락 임베딩 처리 | Recall@30 + 분야·기관 다양성 | 다양성의 비용·효과 확인 |
| **6. 지연 상한** | `collaborative.py`, `recommend.py`, 캐시 관련 파일 | 무거운 통계 폴백 제거, 요청 예산 적용, 입력 버전별 캐시 | cold/warm·동시 요청 p95, 오류 시 지연 | 장애 시 긴 응답 억제 |

2B에서 면허 그룹을 “그룹 안 OR, 그룹 간 AND”로 쓰는 현재 해석도 실제 제한 raw와 공고 사례로 확인해야 합니다. 파싱 불완전한 제한을 SQL로 옮겨 **더 빠르게 잘못 제외하는 것**을 피해야 합니다.

각 변경은 이전 RPC를 유지한 새 이름으로 배포하고, 고정 회사 집합의 shadow 비교 → 제한된 트래픽 → 확대 순서로 진행합니다. 후보·랭커 버전은 추천 캐시에 반영합니다.

---

**4. Postgres RPC 안의 하이브리드 후보 검색 구체안**

**현재 활성 공고 약 1만 건이면 활성 집합에 대한 정확 dense 검색을 우선 유지하겠습니다.** 전체 역사 공고의 IVFFlat 검색으로 돌아가는 변경은 이번 범위에 필요하지 않습니다.

추가할 테이블은 거대한 raw를 매 요청 파싱하는 대신 검색에 필요한 값만 보관합니다.

```text
bid_notice_search
  bid_ntce_no, bid_ntce_ord          복합 PK
  search_text                      공고명·품목·업종·주공종·용역구분
  search_tsv                       simple 설정
  industry_codes text[]
  product_codes text[]
  license_groups jsonb             검증된 그룹별 대체 가능 코드
  allowed_region_codes text[]
  license_state                    unrestricted / parsed / unknown
  region_state                     unrestricted / parsed / unknown
  is_current                       최신 유효 차수 여부
  source_hash, search_version
```

이 테이블은 **제안하는 신규 스키마**입니다. 현재 공고 테이블에 업종·물품 코드 배열은 없습니다. 면허 코드 후보는 `lcns_lmt_nm`의 `/1468` 같은 값과 raw에서 확인할 수 있지만, 물품 코드의 정확한 raw 필드·복수 품목 구조는 실제 적재 데이터를 확인한 뒤 정해야 합니다. 코드가 없다고 이름을 임의로 코드로 바꾸지 않습니다.

검색 문서는 [공고 `build_text()`](/C:/Dev/personal/jodalfit/backend/jobs/embed_bid_notices.py:32)의 도메인 필드를 재사용하되, 기관명은 문자 검색의 핵심 입력에서 우선 제외합니다. 기관 이름으로 관련 없는 업무가 검색되는지 평가할 수 있게 별도 필드로 두면 됩니다.

아래는 **RPC 본문의 SQL 스케치**입니다. 신규 검색 테이블과 `notice_known_ineligible()` 헬퍼를 전제로 하며, 현재 DB에 그대로 실행하는 완성 migration은 아닙니다.

```sql
-- 파라미터:
-- p_vec vector(1536), p_as_of date, p_max_date date
-- p_q tsquery, p_terms text[]
-- p_industry_codes text[], p_product_codes text[]
-- p_region_codes text[], p_company_license_known boolean
-- p_company_region_known boolean, p_count int
--
-- 채널 한도는 초기 실험값: 각각 200, 최종 100.
-- 모두 API에서 상한 검증한다.

with
active as materialized (
  select
    b.bid_ntce_no, b.bid_ntce_ord,
    b.embedding,
    s.search_text, s.search_tsv,
    s.industry_codes, s.product_codes
  from bid_notices b
  join bid_notice_search s
    using (bid_ntce_no, bid_ntce_ord)
  where s.is_current
    and b.bid_ntce_date < p_as_of
    and b.bid_clse_date >= p_as_of
    and b.bid_clse_date <= p_max_date
    and not notice_known_ineligible(
      s.license_state, s.license_groups,
      s.region_state, s.allowed_region_codes,
      p_industry_codes, p_region_codes,
      p_company_license_known, p_company_region_known
    )
),
dense_top as (
  select bid_ntce_no, bid_ntce_ord,
         embedding <=> p_vec as distance
  from active
  where embedding is not null
  order by embedding <=> p_vec, bid_ntce_no, bid_ntce_ord
  limit 200
),
fts_top as (
  select bid_ntce_no, bid_ntce_ord,
         ts_rank_cd(search_tsv, p_q) as relevance
  from active
  where p_q is not null
    and search_tsv @@ p_q
  order by relevance desc, bid_ntce_no, bid_ntce_ord
  limit 200
),
trgm_top as (
  select a.bid_ntce_no, a.bid_ntce_ord,
         max(word_similarity(t.term, a.search_text)) as relevance
  from active a
  cross join unnest(p_terms) as t(term)
  where length(t.term) >= 3
    and t.term <% a.search_text
  group by a.bid_ntce_no, a.bid_ntce_ord
  order by relevance desc, a.bid_ntce_no, a.bid_ntce_ord
  limit 200
),
code_top as (
  select bid_ntce_no, bid_ntce_ord,
    cardinality(array(
      select unnest(industry_codes)
      intersect
      select unnest(p_industry_codes)
    )) +
    cardinality(array(
      select unnest(product_codes)
      intersect
      select unnest(p_product_codes)
    )) as relevance
  from active
  where industry_codes && p_industry_codes
     or product_codes && p_product_codes
  order by relevance desc, bid_ntce_no, bid_ntce_ord
  limit 200
),
ranks as (
  select bid_ntce_no, bid_ntce_ord, 'dense' as channel,
         row_number() over (
           order by distance, bid_ntce_no, bid_ntce_ord
         ) as rank
  from dense_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'fts',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from fts_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'trgm',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from trgm_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'code',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from code_top
),
fused as (
  select bid_ntce_no, bid_ntce_ord,
         sum(1.0 / (60.0 + rank)) as rrf_score,
         array_agg(channel order by channel) as channels
  from ranks
  group by bid_ntce_no, bid_ntce_ord
),
top_candidates as (
  select *
  from fused
  order by rrf_score desc, bid_ntce_no, bid_ntce_ord
  limit p_count
)
select
  t.bid_ntce_no, t.bid_ntce_ord, t.rrf_score, t.channels,
  case when a.embedding is not null
       then 1 - (a.embedding <=> p_vec)
       else null
  end as similarity
from top_candidates t
join active a using (bid_ntce_no, bid_ntce_ord)
order by t.rrf_score desc, t.bid_ntce_no, t.bid_ntce_ord;
```

실装時の要点は以下です。 

- `notice_known_ineligible()`는 **확실한 실패만 true**로 반환합니다. 회사 정보 또는 공고 파싱이 unknown이면 제외하지 않습니다.
- 면허는 각 그룹에 회사가 만족하는 대체 코드가 있는지 검사합니다. 지역은 시도·시군구의 명시적 계층 관계로 검사합니다.
- 업종 제한 코드 일치는 “참가 자격”이지 반드시 “과업 관련성”은 아닙니다. 물품 코드와 별도 채널로 나누는 실험도 필요합니다.
- `p_terms`는 회사 전체 업종 문장 한 개보다 정규화된 분야·물품 용어 최대 8개 정도로 제한합니다. 숫자는 초기 실험값입니다.
- FTS 쿼리는 회사 보유 용어 사이 **OR**로 구성합니다. 전체 업종을 AND로 묶으면 다분야 회사가 다시 불리해집니다.
- RRF 상수 60과 동일 채널 가중치는 출발점입니다. FTS와 trigram이 같은 문자 신호에 이중 가점을 주는지는 채널 제거 실험으로 확인합니다.
- **RRF 점수를 기존 `similarity`에 넣으면 안 됩니다.** `score.py`의 유사도×100은 실제 코사인 유사도를 받도록 유지합니다.
- 임베딩이 없어도 코드·문자 채널로 후보에 들어오게 합니다. 이때 score·MMR에서 누락 벡터를 어떻게 처리할지 명시합니다.

FTS는 `simple`을 쓴다고 한국어 형태소 검색이 완성되지 않습니다. 원문 어절·도메인 용어 일치용으로 사용하고, 붙여쓰기·부분어는 trigram이 보완하도록 설계합니다. `tsquery`와 ranking 사용은 [PostgreSQL 공식 문서](https://www.postgresql.org/docs/current/textsearch-controls.html), word similarity 연산과 인덱스 지원은 [pg_trgm 공식 문서](https://www.postgresql.org/docs/current/pgtrgm.html)에 근거합니다.

**1초 목표를 지키는 방법**

위 스케치는 활성 약 1만 건을 한 번 materialize해 네 채널이 읽습니다. 따라서 내부 문자 채널이 검색 테이블의 GIN 인덱스를 직접 사용한다고 주장하지 않겠습니다.

초기에는 이 단순한 실행계획을 측정합니다. 이후 문자·코드 채널이 병목이면 원본 검색 테이블에서 날짜·현재 차수·자격 조건을 직접 적용하는 분기로 바꿔 인덱스를 쓰게 합니다.

```sql
-- 필요할 때 추가할 인덱스 예시
create index ... on bid_notice_search using gin(search_tsv);
create index ... on bid_notice_search using gin(search_text gin_trgm_ops);
create index ... on bid_notice_search using gin(industry_codes);
create index ... on bid_notice_search using gin(product_codes);
```

GIN trigram은 조건으로 후보를 좁히는 용도입니다. 거리순 KNN top-N을 GIN이 지원한다고 가정하면 안 됩니다. 공식 문서는 그 경우 GiST를 구분합니다. [인덱스 지원 설명](https://www.postgresql.org/docs/current/pgtrgm.html)

검증 기준은 제안값으로:

- RPC p95 ≤ 300ms.
- 설명 제외, 캐시 miss, 사전 계산된 회사 벡터 경로의 전체 응답 p95 ≤ 1초.
- cold buffer·warm buffer, 선택적/광범위 용어, 다분야 회사, 동시 요청 각각 측정.
- `EXPLAIN (ANALYZE, BUFFERS)`로 벡터 읽기·정렬·임시 디스크 사용 확인.
- 통계 캐시 장애 시 해당 보너스를 생략하고 무거운 집계를 실행하지 않음.

**운영 DB 측정 없이 1초를 보장할 수는 없습니다.** 특히 요청 중 외부 임베딩이나 LLM 설명이 포함되는 모드는 별도 지연 목표 또는 스트리밍으로 관리해야 합니다.

---

**5. 다부서 회사: 업종 벡터 + 수주 클러스터 k개**

이 안은 평균 벡터보다 타당합니다. 다만 클러스터를 실제 부서라고 해석하지 말고 **과거 활동 분야**라고 부르는 것이 정확합니다.

신규 테이블:

```text
company_query_vectors
  bizrno_norm
  kind                 industry / history_cluster
  cluster_id
  embedding vector(1536)
  unique_notice_count
  effective_weight
  history_cutoff
  model_version
  source_hash
```

회사 식별 후 이 테이블을 사업자번호로 읽기만 하므로 **회사 벡터 ANN 인덱스를 만들 필요가 없습니다.**

처음부터 k를 자동으로 복잡하게 최적화하지 않습니다.

1. 업종 벡터를 합성 전 상태로 별도 저장합니다.
2. 이력은 회사–공고 단위로 중복 제거합니다.
3. 첫 실험은 낙찰·계약 이력 중심으로 하고, 참가 혼합은 별도로 비교합니다.
4. 정규화 공고 벡터를 배치에서 클러스터링합니다.
5. 초기값은 `k ≤ 3`, 충분한 고유 공고가 없으면 1개 중심점입니다.
6. 작은 클러스터의 유지·병합 기준은 검증 집합에서 결정합니다.
7. 중심점은 기존 반감기 가중 평균 후 정규화합니다.

온라인은 한 RPC에서:

```text
업종 벡터 검색
+ 클러스터 1 검색
+ 클러스터 2 검색
+ 클러스터 3 검색
→ 공고 중복 제거
→ dense 채널 내부 통합
→ 문자·코드 채널과 RRF
→ 기존 랭커
```

**클러스터마다 RRF 한 표씩 주면 안 됩니다.** 벡터가 많은 회사나 비슷한 클러스터를 가진 분야가 과도한 이점을 얻습니다. 초기에는 dense 내부에서 공고별 **최선 순위**를 취해 하나의 dense 채널로 만든 뒤 다른 채널과 합칩니다. 최종 점수용 유사도는 벡터별 코사인과 매칭 벡터 종류를 보관하고, `max cosine` 사용 여부를 평가합니다.

| 측면 | 장점 | 비용·한계 |
|---|---|---|
| 회수 | 소수 분야가 전체 평균에 묻히지 않음 | 과거 일회성 업무도 되살릴 수 있음 |
| 설명 | 어떤 활동 분야 때문에 추천됐는지 추적 가능 | 자동 클러스터 이름은 부정확할 수 있음 |
| 연산 | 클러스터링은 배치, 온라인 CPU 부담 작음 | DB 거리 계산은 벡터 수만큼 증가 |
| 저장 | 기존 공고 임베딩 재사용 가능 | 회사당 벡터 저장·버전 관리 증가 |
| 콜드스타트 | 업종 벡터만으로 동작 | 업종 텍스트 자체가 다분야이면 여전히 희석 |
| 난이도 | 기존 합성 잡에서 재료를 이미 읽음 | 중복 제거·시간 평가·채널 통합은 중간 난이도 |

먼저 업종 벡터 + 수주 평균 벡터 **2개 검색**을 평가하는 작은 실험도 유용합니다. 이 변화만으로 좋아지는지 확인한 뒤 수주 평균을 k개로 확장하면 클러스터링 효과를 분리할 수 있습니다.

활성 집합을 한 번 읽고 여러 쿼리 벡터와 거리 계산하도록 RPC를 구성합니다. 그래도 4개 벡터의 전체 정확 검색이 1초 예산을 넘으면 k를 줄이거나, 활성 공고 전용의 작은 검색 구조를 검토합니다. 전체 역사 공고 ANN 인덱스부터 확장하지 않습니다. pgvector는 정확 검색과 근사 검색을 구분하며, 근사 검색에서는 필터 후 후보 부족을 고려해야 합니다. [pgvector 공식 문서](https://github.com/pgvector/pgvector)

---

**6. 지금 하지 말아야 할 것**

- **KURE-v1 전면 교체와 전체 재임베딩.** 먼저 동일 평가 집합에서 후보 전략 개선 폭을 측정합니다. 모델 비교는 별도 벡터 공간에서 하고 기존 회사 벡터와 섞지 않습니다.
- **미낙찰·미참가를 음성으로 삼아 학습 랭커 만들기.** 노출·검토·참가 기회가 관측되지 않았습니다.
- **요청마다 cross-encoder·LLM reranker 호출.** 소형 CPU와 1초 목표에 맞는 다음 변경이 아닙니다.
- **18만 회사 ANN 협업 검색 복구.** 현재 코드에는 메모리·I/O 문제로 껐다는 명확한 기록이 있습니다. 필요하면 배치 계산부터 검토합니다.
- **처음부터 큰 k, 동적 군집 수, 온라인 클러스터링.** 작은 다중 쿼리 실험으로 효과를 분리해야 합니다.
- **확인불가 자격을 일괄 탈락시키기.** 수집 누락을 추천 누락으로 바꾸게 됩니다.
- **기존 RPC·v1·캐시를 한꺼번에 갈아엎기.** 새 버전과 고정 평가 집합으로 변경 하나씩 비교합니다.
- **README의 흐름을 실제 구현으로 간주하기.** 이번 리뷰에서 이미 선필터·후보 수·협업·MMR 범위가 달랐습니다.
- **낙찰 Recall 상승을 낙찰 확률 상승으로 표현하기.** 이 서비스는 검토할 공고를 발견하는 시스템입니다.

첫 산출물은 새 모델이나 새 랭커가 아니라 **“현재 후보 검색이 어떤 회사 군에서 어느 단계에 정답을 잃는가”를 보여주는 재현 가능한 평가 보고서**여야 합니다. 그 결과가 자격 오제외인지, dense 회수 실패인지, 점수 역전인지 구분해 주면 이후 변경은 훨씬 작고 검증 가능해집니다.
승우님, **우선순위는 `평가 하네스 → 자격·회사 식별 정합성 → 하이브리드 후보 검색 → 다중 벡터 → 점수 조정`입니다. KURE-v1 교체는 그 뒤가 맞습니다.** 후보에서 빠진 공고는 점수나 MMR로 복구할 수 없고, 현재 회사 벡터를 그대로 쓰는 낙찰 held-out 평가는 정답 누수로 성능을 과대평가합니다.

지정한 코드·마이그레이션·문서를 실제로 읽었습니다. 아래는 코드 리뷰와 수정 설계이며, 파일 변경이나 운영 DB 측정은 하지 않았습니다. 성능 수치는 코드 주석에 기록된 과거 측정과 앞으로 검증할 목표를 구분했습니다.

**먼저 현재 흐름을 바로잡아야 합니다.**

| 항목 | 실제 코드 |
|---|---|
| API 기본값 | v2, 후보 200, 결과 20. `recommend.py` 직접 호출 기본값은 v1, 후보 100, 결과 5 |
| 검색량 | RPC에서 `candidate_pool × 2` 조회 → 중복 제거 → `candidate_pool`로 절단 |
| 자격 검사 | 후보 절단 **뒤에** 하드 제외 |
| 유사 회사 기관 +30 | 점수 함수에는 있지만, 파이프라인에서는 비활성화 |
| MMR | 점수 상위 40개에서 **첫 5개만** 다양화, 나머지는 기존 점수순 |
| dense 검색 | 활성 공고를 `MATERIALIZED` CTE로 모은 뒤 **정확 코사인 정렬** |

근거: [API 기본값](/C:/Dev/personal/jodalfit/backend/app/api/recommendations.py:55), [후보 검색](/C:/Dev/personal/jodalfit/backend/app/services/recommend.py:445), [v2 파이프라인](/C:/Dev/personal/jodalfit/backend/app/recommender/pipeline.py:59), [현재 RPC 정의](/C:/Dev/personal/jodalfit/supabase/migrations/0018_match_bid_notices_max_horizon.sql:47).

---

**1. 심각도 순으로 본 결함·비효율**

여기서 P1은 추천 누락·오판 또는 평가를 무효화하는 문제, P2는 순위 품질·응답 지연 문제, P3는 유지보수·표현 문제입니다.

| 심각도 | 파일·함수·줄 | 발견 내용과 영향 |
|---|---|---|
| **P1** | `recommend.py::_search_with_embedding` **445–489**, `pipeline.py::rank_v2` **41–57** | 자격 검사 전에 후보 수를 절단합니다. 가까운 부적격 공고가 후보를 차지하면, 그 아래 적격 공고는 랭커에 도달하지 못합니다. RPC를 2배로 조회해도 자격 검사 전에 다시 절단하므로 해결되지 않습니다. |
| **P1** | `qualifications.py::check_qualifications` **33–45, 61–72** | 면허는 이름·괄호 앞 이름의 교집합, 지역은 시도 또는 문자열 포함으로 판단합니다. 코드·유효기간·상태를 사용하지 않습니다. 세부 업종을 괄호 제거로 같은 자격으로 취급하거나 시군구 제한을 시도 단위로 통과시킬 위험이 있습니다. **실제 오류율은 표본 확인 필요**입니다. |
| **P1** | `recommend.py::_fetch_company_terms` **546–569**, `compute_company_vectors.py::process_chunk` **302–309** | 회사 벡터는 같은 정규화 사업자번호의 여러 회사 행을 합치지만, 온라인 업종 조회는 선택된 `bizrno` 한 행만 읽습니다. 하이픈 행에만 붙은 업종이 누락되면 잘못 제외되거나 확인불가로 통과합니다. |
| **P1** | `pipeline.py::rank_v2` **47–50**, `qualifications.py::check_qualifications` **25–29, 55–59** | 제한 행이 없으면 “제한 없음”입니다. 하지만 제한 수집 실패·미수집과 실제 무제한을 구분할 상태가 없습니다. 회사 정보 부재는 `unverified`지만 공고 제한정보 부재는 검증된 무제한처럼 표시됩니다. |
| **P1 — 평가** | `compute_company_vectors.py::process_chunk` **362–428**, `recommend.py::_fetch_company_history` **754–772**, `0038...sql` **13–20** | 회사 벡터·회사 거래기관·기관 통계가 현재 전체 데이터로 만들어집니다. 이 상태로 과거 낙찰을 숨겨 평가하면 해당 정답 및 이후 거래가 입력에 남습니다. 현재 운영의 버그라기보다 **앞으로 평가를 만들 때 반드시 해결할 문제**입니다. |
| **P2** | `compute_company_vectors.py::build_industry_text` **273–283**, `process_chunk` **430–440, 499–502** | 대표 업종을 중복 강조하고 업종·물품 각각 첫 10개만 넣으며, 수주·참가 공고는 평균 한 개로 합칩니다. 다분야 회사의 소수 분야가 희석됩니다. DB 조회에 명시적 정렬이 없어 어떤 항목이 첫 10개인지도 안정적으로 보장되지 않습니다. |
| **P2** | `compute_company_vectors.py::process_chunk` **413–428** | 계약·참가 건수를 임베딩 존재 확인 **전에** 늘립니다. 임베딩 없는 이력까지 가중치 티어에 영향을 줍니다. 같은 공고의 계약 변경차수·복수 계약도 그대로 평균에 들어가므로 특정 공고가 과대표집될 수 있습니다. 중복 규모는 확인 필요입니다. |
| **P2** | 같은 파일 **440, 484–502** | 수주 평균 벡터를 정규화하지 않고 단위 업종 벡터와 합칩니다. 최종 벡터만 정규화합니다. 따라서 실제 수주 영향은 설정 가중치뿐 아니라 **수주 평균의 노름**, 즉 이력의 응집도에 달려 있습니다. 의도라면 문서화해야 하고, 아니라면 비교 실험이 필요합니다. |
| **P2** | `recommend.py::_search_with_embedding` **466–485** | 같은 공고번호의 차수는 최신본이 아니라 **유사도가 가장 높은 본**이 살아남습니다. 정정으로 자격·마감이 달라졌다면 옛 차수의 조건으로 추천할 수 있습니다. 제목·기관·마감·가격으로 서로 다른 번호도 제거하므로 별개 발주를 합칠 위험도 있습니다. |
| **P2** | `score.py::score_notice` **35–83** | 거래기관 +50, 지역 +30 등은 유사도 차이를 크게 압도할 수 있습니다. 예를 들어 유사도 0.55의 기존 기관 공고가 0.90의 신규 기관 공고보다 먼저 올 수 있습니다. 이것이 나쁜지는 평가해야 하지만, 현재 가중치를 정당화할 측정 근거는 없습니다. |
| **P2** | `score.py` **46–54**, `0038...sql` **15–16** | `1 - distinct_winners / total`은 “고정 거래처 경향”의 충분한 지표가 아닙니다. 100건을 50개 회사가 2건씩 받은 기관도 0.5입니다. 계약 변경차수·반복 계약이 있으면 더 부풀 수 있습니다. 자기 회사가 기존 거래처여도 +50과 −20이 함께 붙습니다. |
| **P2** | `recommend.py::_fetch_company_history` **754–772** | 정렬 없이 500건으로 제한합니다. 최신 이력이라는 보장이 없고 기간도 없습니다. 짝수 개 금액의 중간값은 두 중앙값의 평균이 아니라 위쪽 중앙값입니다. 계약액과 공고 추정가격의 기준 차이도 검토해야 합니다. |
| **P2 — 지연** | `collaborative.py::fetch_institution_stats` **71–94**, `recommend.py::_rpc_with_retry` **53–68** | 캐시 통계 실패 시 무거운 원래 집계로 돌아가고, RPC timeout 후 다시 호출합니다. 주석상 과거 원래 집계는 4–6초였습니다. 캐시 장애 시 1초 목표를 크게 초과할 수 있습니다. |
| **P2 — 지연** | `recommend.py::_recommend_auto` **831–833**, `_recommend_by_keywords` **868–872**, `_recommend_by_company` **937–948** | auto는 회사·키워드 경로를 직렬 실행하고, 키워드 경로의 세 검색도 직렬입니다. 벡터 미보유·키워드 추가 시 요청 중 외부 임베딩 API도 호출합니다. 회사 벡터 검색만 빨라져도 모든 모드의 1초를 보장하지는 못합니다. |
| **P3** | `mmr.py::mmr_diversify` **31–51**, `pipeline.py` **100–108** | 후보 집합의 min–max로 점수를 정규화하므로 같은 점수 차이가 요청마다 다른 의미가 됩니다. 임베딩 누락 후보는 중복 패널티를 받지 않습니다. 현재는 TOP 30 전체의 다양화가 아닙니다. |
| **P3** | `embed_bid_notices.py::fetch_pending` **73–82** | 기본 재임베딩 조건은 `embedded_at IS NULL`뿐입니다. 원문 변경을 임베딩 갱신과 연결하는 해시가 없습니다. **수집 잡이 변경 때 이를 초기화하는지는 추가 확인 필요**입니다. |
| **P3** | `README.md` **85–93, 140**, `CLAUDE.md` **34–36** | 문서는 자격 선필터·협업 시그널을 설명하지만 실제 흐름과 다릅니다. README의 회사 입력 필드도 현재 잡과 일부 다릅니다. 성능 실험 전에 실행 버전과 문서를 맞춰야 합니다. |

주요 코드 링크: [qualifications.py](/C:/Dev/personal/jodalfit/backend/app/recommender/qualifications.py:11), [회사 벡터 합성](/C:/Dev/personal/jodalfit/backend/jobs/compute_company_vectors.py:287), [score.py](/C:/Dev/personal/jodalfit/backend/app/recommender/score.py:22), [MMR](/C:/Dev/personal/jodalfit/backend/app/recommender/mmr.py:18), [통계 폴백](/C:/Dev/personal/jodalfit/backend/app/recommender/collaborative.py:59), [공고 텍스트](/C:/Dev/personal/jodalfit/backend/jobs/embed_bid_notices.py:32).

**반대로 지금 잘 선택한 부분도 있습니다.** 활성 약 1만 건을 먼저 제한하고 정확 정렬하는 RPC는 현재 규모에 합리적입니다. 이를 “ANN 인덱스를 안 타니 결함”으로 보지 않겠습니다. [0016 마이그레이션 3–7줄](/C:/Dev/personal/jodalfit/supabase/migrations/0016_match_rpc_iterative_scan.sql:3)은 이 경로가 과거 약 100ms였다고 기록합니다. 현재 성능은 재측정해야 합니다.

---

**2. 1단계: 과거 낙찰 held-out 평가 하네스**

**정답 라벨이 전혀 없는 것은 아닙니다.** 낙찰·계약은 강한 양성 라벨이고, 참가 결과는 별도의 의도 라벨로 쓸 수 있습니다. 다만 미낙찰·미참가를 부적합 음성으로 취급하면 안 됩니다.

변경 파일 제안:

- 신규 `backend/jobs/evaluate_recommender.py`: 데이터 추출, 시간 분할, 지표·실패 사례 출력.
- 신규 `backend/app/recommender/evaluation.py`: 순수 지표 계산.
- `compute_company_vectors.py`: 벡터 합성 부분에 `as_of`와 입력 이력을 전달할 수 있게 최소 분리.
- `pipeline.py`: `today`와 미리 계산한 기관 통계를 주입할 수 있게 변경.
- `docs/recommender-evaluation.md`: 데이터 범위·누수 제한·실험 규칙.
- 산출물은 `backend/data/recommender_eval/<run_id>/`에 manifest, 지표, 실패 사례 저장.

테스트 프레임워크를 먼저 도입할 필요는 없습니다. 기존 CLI 스타일로 `uv run python -m jobs.evaluate_recommender ...`를 만들고, 지표 계산·시간 경계에 작은 assertion 검증을 붙이면 됩니다.

**A. 양성 라벨 만들기**

기본 단위는 다음입니다.

```text
(company_bizrno_norm, bid_ntce_no, bid_ntce_ord)
```

1. `award_results.is_winner = true`를 정규화 사업자번호로 묶습니다.
2. `contracts.rprsnt_corp_bizrno_norm`과 공고 복합키로 연결해 계약 확인 여부를 붙입니다.
3. 계약은 변경차수·복수 계약으로 양성을 여러 번 세지 않도록 회사–공고 단위로 중복 제거합니다.
4. 계약만 있는 양성도 별도 출처로 포함하되 공고번호·차수 누락, 공고 미연결, 두 출처 충돌은 별도 집계합니다.
5. 차수가 안 맞는다고 공고번호만으로 무조건 연결하지 않습니다. 먼저 수집값과 실제 변경 관계를 확인합니다.

스키마 근거: [contracts 63–88줄](/C:/Dev/personal/jodalfit/supabase/migrations/0001_init.sql:63), [award_results 308–322줄](/C:/Dev/personal/jodalfit/supabase/migrations/0001_init.sql:308), [정규화 컬럼](/C:/Dev/personal/jodalfit/supabase/migrations/0002_bizrno_normalize.sql:10).

라벨은 `winner_only`, `contract_confirmed`, `contract_only`로 나눠 같은 결과를 각각 보고합니다. 관측 가능한 날짜가 부족한 행은 시간 평가에서 제외하고 건수를 표시합니다.

**B. 시간 분할과 추천 상황 복원**

랜덤 낙찰 행 분할을 하지 않습니다. 데이터가 충분한 기간에서 이전 구간은 개발, 그다음 구간은 검증, 마지막 구간은 최종 테스트로 고정합니다. 구체 날짜는 DB의 날짜별 연결 가능한 양성 수를 확인한 뒤 정합니다.

일별 추천 시점 `t`마다 경쟁 후보는 다음입니다.

```text
bid_ntce_date < t
AND bid_clse_date >= t
AND bid_clse_date <= t + 90일
```

날짜만 있으므로 일 경계로 평가하고, 같은 날 공고는 제외하는 보수적 규칙을 사용합니다. 해당 시점에 활성이고 나중에 그 회사가 낙찰한 공고가 held-out 양성입니다.

**후보는 당시 활성 공고 전체입니다.** 양성에 몇 개 랜덤 공고만 섞으면 Recall@100이 실제 서비스보다 훨씬 쉬워집니다.

같은 공고가 여러 날 양성인 점을 고려해:

- 회사–일 단위 Recall을 계산하고,
- 회사별 평균을 낸 뒤 회사 평균을 계산하며,
- 회사–공고 단위 “활성 기간 중 한 번이라도 발견했는가”도 보조로 보고합니다.

목표 공고의 미래 낙찰 사실로 `t`를 고르지 않습니다. 고정된 일별 평가 일정에서 양성이 있는 회사–일을 평가합니다.

**C. 누수 방지 — 가장 중요한 부분**

| 입력 | 평가 규칙 |
|---|---|
| 회사 벡터 | 현재 `companies.embedding` 사용 금지. `t` 이전 이용 가능한 이력으로 재합성 |
| 계약 이력 | 계약일 `< t`. held-out 공고와 동일 공고번호의 모든 차수는 이력에서 제거 |
| 참가 이력 | 개찰 결과가 공개된 시점 `< t`. 단순 투찰 시각만으로 참가 결과를 미리 안 것으로 취급하지 않음 |
| 회사 거래기관·금액 | 같은 cutoff로 재계산. 현재 온라인 함수 호출 금지 |
| 기관 반복 통계 | 전체 회사의 계약에서 `< t` 조건으로 계산. 현재 MV 사용 금지 |
| 클러스터 | 평가 시점 이전 이력으로만 생성 |
| 점수·MMR | `date.today()` 대신 `t` 주입 |
| 정정·재공고 | 관련 공고가 train과 held-out 양쪽에 들어가 답을 노출하지 않는지 확인 |
| 캐시 | 운영 추천 캐시 사용 금지. 실험 설정·시점·입력 해시로 별도 캐시 |

`award_results.raw->>bidprcDt`는 현재 잡에서 읽지만, 이름만으로 **결과 공개 시각이라고 가정하면 안 됩니다**. `bid_notices.openg_date`와 raw 실제 필드를 대조하고, 판단 불가능한 참가 이력은 엄격 평가에서 제외합니다.

**현재 DB만으로 완전한 과거 운영 재현은 어렵습니다.** 회사 업종·지역의 과거 변경 이력과 공고 정정본의 당시 상태가 완전히 보존되었다는 근거가 없습니다. `created_at`도 과거 데이터를 나중에 백필한 적재 시각일 수 있습니다.

따라서 결과를 두 가지로 분리합니다.

- **시간 통제 평가:** 날짜가 확인되는 과거 이력만 사용. 회사 등록정보도 당시 존재를 확인할 수 있는 범위만 사용.
- **현재 등록정보 참고 평가:** 현재 업종·물품·지역을 고정해 후보 알고리즘을 비교. 과거 추천 성능으로 주장하지 않음.

앞으로는 일별 회사 프로필·공고 상태·검색 입력 버전을 저장해야 진짜 운영 재현 평가가 가능합니다.

**D. 반드시 보고할 지표**

```text
Recall@100 = |양성 ∩ 최종 후보 100| / |양성|
Recall@30  = |양성 ∩ 최종 결과 30| / |양성|
```

추가로:

- 자격 검사 전 후보 Recall@100.
- 자격 검사 후 후보 Recall@100.
- MMR 전·후 Recall@30.
- 후보 합집합 Recall: 각 검색 채널이 정답을 가져왔는지.
- 회사 macro 평균과 전체 양성 micro 평균.
- 최종 결과 30개 충족률, 확인불가 비율, 양성의 자격 오제외율.
- p50/p95/p99 응답시간과 RPC 시간, 캐시 hit/miss 분리.

회사 군은 **추천 시점 이전 정보**로 만듭니다.

| 군 | 기준 |
|---|---|
| 콜드스타트 | 과거 계약·참가 이력 0 |
| 소이력 / 풍부한 이력 | 중복 제거 이력 1–5 / 6+ |
| 단일 / 다분야 | 업종·물품 상위 분류와 과거 공고 분야 분산. 정확한 “부서” 라벨로 부르지 않음 |
| 데이터 완전 / 불완전 | 업종·지역·물품 확보 여부 |
| 업무구분 | 공사·용역·물품 |
| 지역 | 표본 충분한 지역만 비교 |

낙찰 라벨은 기존 거래처·성공 업체 편향이 있습니다. 그래서 낙찰 Recall만 최적화하지 말고 `award_results.is_winner = false`의 참가 공고 발견률을 별도로 확인하고, 실패·개선 사례를 수동 검토해야 합니다.

검증은 같은 평가 집합의 paired 비교로 합니다. 회사 단위 bootstrap 신뢰구간을 붙이고, 작은 회사 군의 상승·하락을 전체 평균에 숨기지 않습니다.

---

**3. 이후 수정은 작게 나눕니다**

| 단계 | 변경 파일 | 핵심 로직 | 검증 | 예상 효과 |
|---|---|---|---|---|
| **1. 평가 하네스** | 위 신규 CLI·평가 모듈, 벡터 잡·pipeline 최소 수정 | 시간 분할, 이력 재합성, 단계별 Recall | 누수 assertion, 연결률·군별 baseline | 이후 변경의 효과 판단 가능 |
| **2A. 회사 정합성** | `recommend.py` | 정규화 사업자번호의 모든 PK에 연결된 업종·물품 통합. 이름 trim·결정적 정렬 | 하이픈 중복 회사 표본, baseline 대비 오제외 | 벡터와 자격 입력 불일치 제거 |
| **2B. 자격 정합성** | `qualifications.py`, 제한 수집 잡, 신규 migration | 코드 기반 자격, 유효기간·상태, 지역 코드. `pass/fail/unknown` 구분 | 그룹 OR/AND·시군구·기간 경계 assertion, 과거 낙찰 오제외 수동 확인 | 잘못된 통과·제외 감소 |
| **2C. 후보 선필터** | 신규 RPC migration, `recommend.py`, `pipeline.py` | 확실한 자격 실패만 검색 전 제외. 공고 최신 유효 차수 선정 | Recall@100, 30개 충족률, SQL 실행계획 | 부적격 공고의 후보 점유 제거 |
| **3A. dense + 코드** | 검색용 테이블 잡·migration, 새 RPC | 코드 채널과 dense를 RRF로 결합 | 채널별 정답 유입, 후보 Recall@100 | 코드가 분명한 전문 분야 회수 |
| **3B. 문자 검색 추가** | 같은 RPC, `embed_bid_notices.py`의 텍스트 생성 부분 재사용 | FTS·trigram 채널 추가 | dense-only 대비 Recall, 실패 사례 | 고유 품목명·복합어 공고 회수 |
| **4. 다중 벡터** | `compute_company_vectors.py`, 다중 벡터 테이블·RPC, `recommend.py` | 업종 벡터 + 수주 클러스터 최대 3개 | 다분야 회사 Recall@100/@30, 지연 | 평균에 묻힌 분야 회수 |
| **5A. 이력·기관 점수** | `recommend.py`, `score.py`, 통계 잡·migration | 최근 중복 제거 이력, 정확한 median. 기관 보너스·개방성 항목 각각 ablation | Recall@30, 신규 기관 발견, 수동 적합성 | 검증된 순위 개선 |
| **5B. MMR 조정** | `mmr.py`, `pipeline.py` | 끄기/첫 5개/전체 30개 비교. 누락 임베딩 처리 | Recall@30 + 분야·기관 다양성 | 다양성의 비용·효과 확인 |
| **6. 지연 상한** | `collaborative.py`, `recommend.py`, 캐시 관련 파일 | 무거운 통계 폴백 제거, 요청 예산 적용, 입력 버전별 캐시 | cold/warm·동시 요청 p95, 오류 시 지연 | 장애 시 긴 응답 억제 |

2B에서 면허 그룹을 “그룹 안 OR, 그룹 간 AND”로 쓰는 현재 해석도 실제 제한 raw와 공고 사례로 확인해야 합니다. 파싱 불완전한 제한을 SQL로 옮겨 **더 빠르게 잘못 제외하는 것**을 피해야 합니다.

각 변경은 이전 RPC를 유지한 새 이름으로 배포하고, 고정 회사 집합의 shadow 비교 → 제한된 트래픽 → 확대 순서로 진행합니다. 후보·랭커 버전은 추천 캐시에 반영합니다.

---

**4. Postgres RPC 안의 하이브리드 후보 검색 구체안**

**현재 활성 공고 약 1만 건이면 활성 집합에 대한 정확 dense 검색을 우선 유지하겠습니다.** 전체 역사 공고의 IVFFlat 검색으로 돌아가는 변경은 이번 범위에 필요하지 않습니다.

추가할 테이블은 거대한 raw를 매 요청 파싱하는 대신 검색에 필요한 값만 보관합니다.

```text
bid_notice_search
  bid_ntce_no, bid_ntce_ord          복합 PK
  search_text                      공고명·품목·업종·주공종·용역구분
  search_tsv                       simple 설정
  industry_codes text[]
  product_codes text[]
  license_groups jsonb             검증된 그룹별 대체 가능 코드
  allowed_region_codes text[]
  license_state                    unrestricted / parsed / unknown
  region_state                     unrestricted / parsed / unknown
  is_current                       최신 유효 차수 여부
  source_hash, search_version
```

이 테이블은 **제안하는 신규 스키마**입니다. 현재 공고 테이블에 업종·물품 코드 배열은 없습니다. 면허 코드 후보는 `lcns_lmt_nm`의 `/1468` 같은 값과 raw에서 확인할 수 있지만, 물품 코드의 정확한 raw 필드·복수 품목 구조는 실제 적재 데이터를 확인한 뒤 정해야 합니다. 코드가 없다고 이름을 임의로 코드로 바꾸지 않습니다.

검색 문서는 [공고 `build_text()`](/C:/Dev/personal/jodalfit/backend/jobs/embed_bid_notices.py:32)의 도메인 필드를 재사용하되, 기관명은 문자 검색의 핵심 입력에서 우선 제외합니다. 기관 이름으로 관련 없는 업무가 검색되는지 평가할 수 있게 별도 필드로 두면 됩니다.

아래는 **RPC 본문의 SQL 스케치**입니다. 신규 검색 테이블과 `notice_known_ineligible()` 헬퍼를 전제로 하며, 현재 DB에 그대로 실행하는 완성 migration은 아닙니다.

```sql
-- 파라미터:
-- p_vec vector(1536), p_as_of date, p_max_date date
-- p_q tsquery, p_terms text[]
-- p_industry_codes text[], p_product_codes text[]
-- p_region_codes text[], p_company_license_known boolean
-- p_company_region_known boolean, p_count int
--
-- 채널 한도는 초기 실험값: 각각 200, 최종 100.
-- 모두 API에서 상한 검증한다.

with
active as materialized (
  select
    b.bid_ntce_no, b.bid_ntce_ord,
    b.embedding,
    s.search_text, s.search_tsv,
    s.industry_codes, s.product_codes
  from bid_notices b
  join bid_notice_search s
    using (bid_ntce_no, bid_ntce_ord)
  where s.is_current
    and b.bid_ntce_date < p_as_of
    and b.bid_clse_date >= p_as_of
    and b.bid_clse_date <= p_max_date
    and not notice_known_ineligible(
      s.license_state, s.license_groups,
      s.region_state, s.allowed_region_codes,
      p_industry_codes, p_region_codes,
      p_company_license_known, p_company_region_known
    )
),
dense_top as (
  select bid_ntce_no, bid_ntce_ord,
         embedding <=> p_vec as distance
  from active
  where embedding is not null
  order by embedding <=> p_vec, bid_ntce_no, bid_ntce_ord
  limit 200
),
fts_top as (
  select bid_ntce_no, bid_ntce_ord,
         ts_rank_cd(search_tsv, p_q) as relevance
  from active
  where p_q is not null
    and search_tsv @@ p_q
  order by relevance desc, bid_ntce_no, bid_ntce_ord
  limit 200
),
trgm_top as (
  select a.bid_ntce_no, a.bid_ntce_ord,
         max(word_similarity(t.term, a.search_text)) as relevance
  from active a
  cross join unnest(p_terms) as t(term)
  where length(t.term) >= 3
    and t.term <% a.search_text
  group by a.bid_ntce_no, a.bid_ntce_ord
  order by relevance desc, a.bid_ntce_no, a.bid_ntce_ord
  limit 200
),
code_top as (
  select bid_ntce_no, bid_ntce_ord,
    cardinality(array(
      select unnest(industry_codes)
      intersect
      select unnest(p_industry_codes)
    )) +
    cardinality(array(
      select unnest(product_codes)
      intersect
      select unnest(p_product_codes)
    )) as relevance
  from active
  where industry_codes && p_industry_codes
     or product_codes && p_product_codes
  order by relevance desc, bid_ntce_no, bid_ntce_ord
  limit 200
),
ranks as (
  select bid_ntce_no, bid_ntce_ord, 'dense' as channel,
         row_number() over (
           order by distance, bid_ntce_no, bid_ntce_ord
         ) as rank
  from dense_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'fts',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from fts_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'trgm',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from trgm_top

  union all

  select bid_ntce_no, bid_ntce_ord, 'code',
         row_number() over (
           order by relevance desc, bid_ntce_no, bid_ntce_ord
         )
  from code_top
),
fused as (
  select bid_ntce_no, bid_ntce_ord,
         sum(1.0 / (60.0 + rank)) as rrf_score,
         array_agg(channel order by channel) as channels
  from ranks
  group by bid_ntce_no, bid_ntce_ord
),
top_candidates as (
  select *
  from fused
  order by rrf_score desc, bid_ntce_no, bid_ntce_ord
  limit p_count
)
select
  t.bid_ntce_no, t.bid_ntce_ord, t.rrf_score, t.channels,
  case when a.embedding is not null
       then 1 - (a.embedding <=> p_vec)
       else null
  end as similarity
from top_candidates t
join active a using (bid_ntce_no, bid_ntce_ord)
order by t.rrf_score desc, t.bid_ntce_no, t.bid_ntce_ord;
```

실装時の要点は以下です。 

- `notice_known_ineligible()`는 **확실한 실패만 true**로 반환합니다. 회사 정보 또는 공고 파싱이 unknown이면 제외하지 않습니다.
- 면허는 각 그룹에 회사가 만족하는 대체 코드가 있는지 검사합니다. 지역은 시도·시군구의 명시적 계층 관계로 검사합니다.
- 업종 제한 코드 일치는 “참가 자격”이지 반드시 “과업 관련성”은 아닙니다. 물품 코드와 별도 채널로 나누는 실험도 필요합니다.
- `p_terms`는 회사 전체 업종 문장 한 개보다 정규화된 분야·물품 용어 최대 8개 정도로 제한합니다. 숫자는 초기 실험값입니다.
- FTS 쿼리는 회사 보유 용어 사이 **OR**로 구성합니다. 전체 업종을 AND로 묶으면 다분야 회사가 다시 불리해집니다.
- RRF 상수 60과 동일 채널 가중치는 출발점입니다. FTS와 trigram이 같은 문자 신호에 이중 가점을 주는지는 채널 제거 실험으로 확인합니다.
- **RRF 점수를 기존 `similarity`에 넣으면 안 됩니다.** `score.py`의 유사도×100은 실제 코사인 유사도를 받도록 유지합니다.
- 임베딩이 없어도 코드·문자 채널로 후보에 들어오게 합니다. 이때 score·MMR에서 누락 벡터를 어떻게 처리할지 명시합니다.

FTS는 `simple`을 쓴다고 한국어 형태소 검색이 완성되지 않습니다. 원문 어절·도메인 용어 일치용으로 사용하고, 붙여쓰기·부분어는 trigram이 보완하도록 설계합니다. `tsquery`와 ranking 사용은 [PostgreSQL 공식 문서](https://www.postgresql.org/docs/current/textsearch-controls.html), word similarity 연산과 인덱스 지원은 [pg_trgm 공식 문서](https://www.postgresql.org/docs/current/pgtrgm.html)에 근거합니다.

**1초 목표를 지키는 방법**

위 스케치는 활성 약 1만 건을 한 번 materialize해 네 채널이 읽습니다. 따라서 내부 문자 채널이 검색 테이블의 GIN 인덱스를 직접 사용한다고 주장하지 않겠습니다.

초기에는 이 단순한 실행계획을 측정합니다. 이후 문자·코드 채널이 병목이면 원본 검색 테이블에서 날짜·현재 차수·자격 조건을 직접 적용하는 분기로 바꿔 인덱스를 쓰게 합니다.

```sql
-- 필요할 때 추가할 인덱스 예시
create index ... on bid_notice_search using gin(search_tsv);
create index ... on bid_notice_search using gin(search_text gin_trgm_ops);
create index ... on bid_notice_search using gin(industry_codes);
create index ... on bid_notice_search using gin(product_codes);
```

GIN trigram은 조건으로 후보를 좁히는 용도입니다. 거리순 KNN top-N을 GIN이 지원한다고 가정하면 안 됩니다. 공식 문서는 그 경우 GiST를 구분합니다. [인덱스 지원 설명](https://www.postgresql.org/docs/current/pgtrgm.html)

검증 기준은 제안값으로:

- RPC p95 ≤ 300ms.
- 설명 제외, 캐시 miss, 사전 계산된 회사 벡터 경로의 전체 응답 p95 ≤ 1초.
- cold buffer·warm buffer, 선택적/광범위 용어, 다분야 회사, 동시 요청 각각 측정.
- `EXPLAIN (ANALYZE, BUFFERS)`로 벡터 읽기·정렬·임시 디스크 사용 확인.
- 통계 캐시 장애 시 해당 보너스를 생략하고 무거운 집계를 실행하지 않음.

**운영 DB 측정 없이 1초를 보장할 수는 없습니다.** 특히 요청 중 외부 임베딩이나 LLM 설명이 포함되는 모드는 별도 지연 목표 또는 스트리밍으로 관리해야 합니다.

---

**5. 다부서 회사: 업종 벡터 + 수주 클러스터 k개**

이 안은 평균 벡터보다 타당합니다. 다만 클러스터를 실제 부서라고 해석하지 말고 **과거 활동 분야**라고 부르는 것이 정확합니다.

신규 테이블:

```text
company_query_vectors
  bizrno_norm
  kind                 industry / history_cluster
  cluster_id
  embedding vector(1536)
  unique_notice_count
  effective_weight
  history_cutoff
  model_version
  source_hash
```

회사 식별 후 이 테이블을 사업자번호로 읽기만 하므로 **회사 벡터 ANN 인덱스를 만들 필요가 없습니다.**

처음부터 k를 자동으로 복잡하게 최적화하지 않습니다.

1. 업종 벡터를 합성 전 상태로 별도 저장합니다.
2. 이력은 회사–공고 단위로 중복 제거합니다.
3. 첫 실험은 낙찰·계약 이력 중심으로 하고, 참가 혼합은 별도로 비교합니다.
4. 정규화 공고 벡터를 배치에서 클러스터링합니다.
5. 초기값은 `k ≤ 3`, 충분한 고유 공고가 없으면 1개 중심점입니다.
6. 작은 클러스터의 유지·병합 기준은 검증 집합에서 결정합니다.
7. 중심점은 기존 반감기 가중 평균 후 정규화합니다.

온라인은 한 RPC에서:

```text
업종 벡터 검색
+ 클러스터 1 검색
+ 클러스터 2 검색
+ 클러스터 3 검색
→ 공고 중복 제거
→ dense 채널 내부 통합
→ 문자·코드 채널과 RRF
→ 기존 랭커
```

**클러스터마다 RRF 한 표씩 주면 안 됩니다.** 벡터가 많은 회사나 비슷한 클러스터를 가진 분야가 과도한 이점을 얻습니다. 초기에는 dense 내부에서 공고별 **최선 순위**를 취해 하나의 dense 채널로 만든 뒤 다른 채널과 합칩니다. 최종 점수용 유사도는 벡터별 코사인과 매칭 벡터 종류를 보관하고, `max cosine` 사용 여부를 평가합니다.

| 측면 | 장점 | 비용·한계 |
|---|---|---|
| 회수 | 소수 분야가 전체 평균에 묻히지 않음 | 과거 일회성 업무도 되살릴 수 있음 |
| 설명 | 어떤 활동 분야 때문에 추천됐는지 추적 가능 | 자동 클러스터 이름은 부정확할 수 있음 |
| 연산 | 클러스터링은 배치, 온라인 CPU 부담 작음 | DB 거리 계산은 벡터 수만큼 증가 |
| 저장 | 기존 공고 임베딩 재사용 가능 | 회사당 벡터 저장·버전 관리 증가 |
| 콜드스타트 | 업종 벡터만으로 동작 | 업종 텍스트 자체가 다분야이면 여전히 희석 |
| 난이도 | 기존 합성 잡에서 재료를 이미 읽음 | 중복 제거·시간 평가·채널 통합은 중간 난이도 |

먼저 업종 벡터 + 수주 평균 벡터 **2개 검색**을 평가하는 작은 실험도 유용합니다. 이 변화만으로 좋아지는지 확인한 뒤 수주 평균을 k개로 확장하면 클러스터링 효과를 분리할 수 있습니다.

활성 집합을 한 번 읽고 여러 쿼리 벡터와 거리 계산하도록 RPC를 구성합니다. 그래도 4개 벡터의 전체 정확 검색이 1초 예산을 넘으면 k를 줄이거나, 활성 공고 전용의 작은 검색 구조를 검토합니다. 전체 역사 공고 ANN 인덱스부터 확장하지 않습니다. pgvector는 정확 검색과 근사 검색을 구분하며, 근사 검색에서는 필터 후 후보 부족을 고려해야 합니다. [pgvector 공식 문서](https://github.com/pgvector/pgvector)

---

**6. 지금 하지 말아야 할 것**

- **KURE-v1 전면 교체와 전체 재임베딩.** 먼저 동일 평가 집합에서 후보 전략 개선 폭을 측정합니다. 모델 비교는 별도 벡터 공간에서 하고 기존 회사 벡터와 섞지 않습니다.
- **미낙찰·미참가를 음성으로 삼아 학습 랭커 만들기.** 노출·검토·참가 기회가 관측되지 않았습니다.
- **요청마다 cross-encoder·LLM reranker 호출.** 소형 CPU와 1초 목표에 맞는 다음 변경이 아닙니다.
- **18만 회사 ANN 협업 검색 복구.** 현재 코드에는 메모리·I/O 문제로 껐다는 명확한 기록이 있습니다. 필요하면 배치 계산부터 검토합니다.
- **처음부터 큰 k, 동적 군집 수, 온라인 클러스터링.** 작은 다중 쿼리 실험으로 효과를 분리해야 합니다.
- **확인불가 자격을 일괄 탈락시키기.** 수집 누락을 추천 누락으로 바꾸게 됩니다.
- **기존 RPC·v1·캐시를 한꺼번에 갈아엎기.** 새 버전과 고정 평가 집합으로 변경 하나씩 비교합니다.
- **README의 흐름을 실제 구현으로 간주하기.** 이번 리뷰에서 이미 선필터·후보 수·협업·MMR 범위가 달랐습니다.
- **낙찰 Recall 상승을 낙찰 확률 상승으로 표현하기.** 이 서비스는 검토할 공고를 발견하는 시스템입니다.

첫 산출물은 새 모델이나 새 랭커가 아니라 **“현재 후보 검색이 어떤 회사 군에서 어느 단계에 정답을 잃는가”를 보여주는 재현 가능한 평가 보고서**여야 합니다. 그 결과가 자격 오제외인지, dense 회수 실패인지, 점수 역전인지 구분해 주면 이후 변경은 훨씬 작고 검증 가능해집니다.
