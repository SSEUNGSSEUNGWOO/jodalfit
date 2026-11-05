# Gemini embedding-001(768d) 전환 계획 — 2026-11-05

근거: `docs/recommender/exp-2026-11-04-embedding-rematch.md` (final@20 3시점 평균 0.513 → 0.580, 10/1 홀드아웃 0.640 → 0.689).
외부 검토(Codex, 2026-11-05): 조건부 찬성 — "운영 경로 재현과 실제 롤백 검증이 먼저".

## 원칙
1. **전환 전까지 운영이 읽는 것은 하나도 바뀌지 않는다.** 열·RPC·코드 경로 전부 KURE 옆에 덧붙이고, `EMBED_SPACE=gemini` 일 때만 깨어난다.
2. 되돌림은 환경변수 하나(`EMBED_SPACE`, `NEXT_PUBLIC_EMBED_SPACE`, 리포 Variables `EMBED_SPACE`). KURE 열은 전환 뒤 한두 달 유지.
3. 채택 조건: 운영 RPC 경로로 돌린 채점표가 7/1·8/1·9/1 전부 KURE 위 + cold/small/rich 어느 군도 안 떨어짐 + 10/1 유지 + 키워드 채점표 KURE 이상 + 블라인드 40문항에서 지는 수 ≤ 이기는 수.

## 단계
| # | 단계 | 운영 영향 | 검증 |
|---|---|---|---|
| 1 | 0067 마이그레이션: `embedding_g vector(768)`·`embedded_g_at` 4개 표 + `text_embeddings.embedding_g` + `_g` RPC 9개(match 4·similar_notice_awardees·update 4) | 없음(열 추가는 메타데이터, 함수는 신규) | 함수 존재·빈 결과 반환 확인 |
| 2 | 백엔드: `embedding.py` 에 `gemini` 공간(REST batchEmbedContents, taskType 문서/질의 분리, 768d, 재시도·타임아웃·차단기), `_rpc_name/_emb_col`·잡·하네스의 공간 분기에 `gemini` 추가, 캐시 열 분기 | 없음(kure 경로 그대로) | `python -m app.services.embedding` 자체 점검, kure 로 로컬 추천 동일 |
| 3 | 프런트: `embed-space.ts` 에 gemini 분기(`embedding_g`, `_g` RPC) | 없음 | lint·build |
| 4 | 백필: 공고 416k·사전규격 68k·발주계획 12k → `_g`, 회사 벡터 91k(업종 텍스트 = RETRIEVAL_QUERY, 이력 공고 = `_g`) | DB 쓰기 부하 — 배치 작게, 밤, 응답 시간 감시 | 건수·null 0 |
| 5 | 인덱스: bid_notices ivfflat halfvec(768) lists 600, pre_specs/order_plans/companies hnsw — 전부 concurrently | 없음 | idx_scan 증가 |
| 6 | 검증: 채점표 `--space gemini`(DB RPC 경로, npz 없이) 7/1·8/1·9/1·10/1 vs kure 같은 날 재실행; 키워드 채점표(사전규격·발주계획 → 전환 공고 연결 정답) 양쪽; 블라인드 40문항 페이지 | 없음(읽기만, 병렬 ≤4) | 채택 조건 |
| 7 | 전환: Railway `EMBED_SPACE=gemini` → Vercel `NEXT_PUBLIC_EMBED_SPACE=gemini` → 리포 Variables → check_*.py 9종 + 운영 Server-Timing | **전환** | 롤백 = 변수 되돌리기 |
| 8 | 정리(한두 달 뒤): KURE·OpenAI 열·RPC·인덱스 삭제, Railway 에서 onnxruntime 제거 | 저장 공간 감소 | — |

## 선행(승우님)
- Google AI Studio: 결제 연결된 프로젝트에서 새 키 발급, 채팅에 올린 옛 키 삭제. `backend/.env` 의 `GEMINI_API_KEY` 에 직접 기입(채팅 금지). 예산 알림 월 $10.
- 새 키를 Railway 변수·GitHub Actions 시크릿에 넣는 것은 이쪽에서.

## 결정 사항
- 차원 768(MRL). pgvector `vector(768)` + HNSW 가능하나 bid_notices 는 0032·0045 전례대로 ivfflat halfvec.
- taskType: 공고·사전규격·발주계획 = `RETRIEVAL_DOCUMENT`, 업종 텍스트·키워드 질의 = `RETRIEVAL_QUERY`(실험 그대로). 캐시 키는 (space, sha1) — 질의/문서가 같은 글일 일은 없어 taskType 을 키에 안 넣는다.
- 키워드 모드 임베딩은 지금도 제목 일치 SQL 과 병렬이라 순 증가 ≈ 90ms. 장애 시: 캐시 → 제목 일치만 → 차단기(실패 뒤 60초 건너뜀).
- 점수표·입력 텍스트·풀 200 은 그대로. 전환 뒤 `sweep_score_scale` 로 배율 k 만 훑는다(별도 실험).
