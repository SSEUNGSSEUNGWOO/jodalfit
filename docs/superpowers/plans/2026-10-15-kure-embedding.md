# 임베딩 모델 전환 (OpenAI text-embedding-3-small → KURE-v1) 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. 각 Task 끝에 커밋, push 는 컨트롤러.

**Goal:** 후보 검색 벡터 공간을 KURE-v1(1024d)로 바꾼다. 근거: `docs/recommender/exp-2026-10-15-embedding-model.md` — dense 0.55→0.63, final@30 0.395→0.438, 3시점 일관.

**Architecture (요약):**
- **두 공간 병행**: 기존 `embedding vector(1536)` 은 그대로 두고 `embedding_k vector(1024)` 컬럼을 4개 테이블(bid_notices, companies, pre_specs, order_plans)에 추가. 설정 `EMBED_SPACE=openai|kure` 가 어느 컬럼·RPC·임베딩 함수를 쓸지 고른다. 롤백 = 환경변수 하나.
- **모델 서빙 3곳**: ① 최초 백필 = 노트북 GPU(fp16, `docs/recommender/scripts/embed_local.py` 계열), ② 매일 배치 = GitHub Actions CPU(ONNX int8), ③ 요청 시점(키워드 모드·벡터 없는 회사·회사+키워드) = Railway 프로세스 안 ONNX int8. ②③은 같은 ONNX 파일을 GitHub Release 자산에서 받는다.
- **텍스트는 그대로**: `embed_bid_notices.build_text`, `compute_company_vectors.build_industry_text`, 사전규격·발주계획 빌더. 실험과 동일 조건.
- **RPC**: `match_bid_notices` 등 5개에 `_k` 변형(1024d, `embedding_k` 컬럼) 추가. 본문은 기존과 동일, 컬럼·타입만 다름. 프론트의 직접 RPC 호출 2곳(회사 페이지)도 설정에 따라 `_k` 사용.
- **점수표**: KURE 유사도 분포가 다르므로 하네스로 재보정(Task 7). 전환 전후 비교는 하네스 `--space kure` 로.

**Tech:** onnxruntime + optimum(export, 노트북에서 1회), tokenizers, pgvector halfvec 인덱스, GitHub Release 자산(모델 파일 ~560MB int8).

---

### Task 1: ONNX int8 모델 만들기 + 공용 임베딩 모듈

**Files:** Create `backend/app/services/local_embed.py`, Create `docs/recommender/scripts/export_kure_onnx.py`(노트북 torch env 용), Modify `backend/pyproject.toml`(`uv add onnxruntime tokenizers huggingface-hub`), Modify `backend/app/core/config.py`

- [ ] Step 1 `export_kure_onnx.py` (torch env `C:\dev\ops\jodalfit\design\.venv`): `optimum.exporters.onnx` 로 `nlpai-lab/KURE-v1` 을 ONNX(fp32) export → `onnxruntime.quantization.quantize_dynamic`(QInt8, weights only) → `kure-v1-int8.onnx` + `tokenizer.json`. 200개 공고 텍스트로 fp16 GPU 임베딩과 int8 ONNX 임베딩의 코사인 평균·최소를 출력(기준: 평균 ≥ 0.995, 최소 ≥ 0.98). 출력 폴더를 zip 으로 묶어 GitHub Release `models-kure-v1-int8` 자산으로 업로드(`gh release create models-kure-v1-int8 kure-v1-int8.zip --notes ...`).
- [ ] Step 2 `local_embed.py`:
  ```python
  """KURE-v1 (ONNX int8) 로컬 임베딩 — 요청 시점(Railway)·매일 배치(Actions) 공용. 모델 파일은 GitHub Release 자산에서 첫 호출 때 받아 캐시."""
  MODEL_URL = "https://github.com/SSEUNGSSEUNGWOO/jodalfit/releases/download/models-kure-v1-int8/kure-v1-int8.zip"
  CACHE_DIR = Path(os.environ.get("KURE_MODEL_DIR", Path(tempfile.gettempdir()) / "kure-v1-int8"))
  DIM = 1024; MAX_LEN = 512
  @lru_cache
  def _session(): ...  # 다운로드(없으면) → onnxruntime.InferenceSession(providers=["CPUExecutionProvider"], intra_op_num_threads=min(4, os.cpu_count()))
  def embed_texts_kure(texts: list[str], batch: int = 16) -> list[list[float]]:
      # tokenizers 로 토크나이즈(truncation 512, padding longest) → ORT run → CLS pooling(KURE/bge-m3 = CLS) → L2 정규화
  ```
  CLS pooling 인지 mean pooling 인지는 sentence-transformers 설정(`1_Pooling/config.json`, bge-m3 는 cls)로 확인해 주석에 적는다.
- [ ] Step 3 config: `embed_space: Literal["openai", "kure"] = "openai"` (전환 전 기본 openai), `kure_model_dir: str | None = None`.
- [ ] Step 4 `app/services/embedding.py`(신규, 얇은 스위치): `embed_texts(texts, space=None)` → space(기본 settings.embed_space) 가 kure 면 `embed_texts_kure`, 아니면 기존 OpenAI `openai_client.embed_texts`. `dim(space)` 도 제공. 기존 호출부 8곳은 이 스위치를 import 하도록 바꾼다(기능 변화 없음, 기본 openai).
- [ ] Step 5 자체 점검: `uv run python -m app.services.local_embed` → 모델 받고 3문장 임베딩, dim 1024, 정규화 확인, 1문장 지연(ms) 출력. 커밋.

### Task 2: 마이그레이션 0045 — `embedding_k` 컬럼 + RPC `_k` 변형

**Files:** Create `supabase/migrations/0045_kure_embedding_space.sql`
- 4개 테이블에 `embedding_k vector(1024)` 추가(없으면).
- RPC: `match_bid_notices_k`(0044 본문 복사, `b.embedding_k`, `query_embedding vector(1024)`), `match_pre_specs_k`, `match_order_plans_k`, `match_companies_k`, `similar_notice_awardees_k` — 각각 최신 정의(0010·0009·0003/0016·0031·0044)를 그대로 복사하고 컬럼·타입만 교체. 반환 타입 동일.
- 인덱스는 **백필 뒤** 별도(Task 4)에서: `bid_notices` 는 0032 와 같은 `ivfflat ((embedding_k::halfvec(1024)) halfvec_cosine_ops)`, pre_specs·order_plans 는 hnsw, companies 는 0031 방식.
- `notify pgrst, 'reload schema'`. 적용은 승우님 Dashboard. 커밋.

### Task 3: 배치 잡에 공간 스위치

**Files:** Modify `jobs/embed_bid_notices.py`, `jobs/embed_pre_specs.py`, `jobs/embed_order_plans.py`, `jobs/compute_company_vectors.py`
- **업종 텍스트 임베딩 캐시**(필수): `compute_company_vectors` 는 매일 2.5만 회사의 업종 텍스트를 다시 임베딩한다(2026-10-15 실측 24h 5.9만 건). OpenAI 는 싸서 괜찮았지만 로컬 CPU 모델은 시간당 1만 건이 한계 → 0045 에 `text_embeddings(space text, text_sha1 text, embedding vector(1024), created_at) primary key(space, text_sha1)` 테이블 추가(또는 0046), `embedding.embed_texts(..., cache=True)` 가 캐시 조회 → 미스만 모델 호출 → 저장. 공고는 캐시 불필요(한 번만 임베딩).
- 백엔드 2개: 배치는 `KURE_BACKEND=torch`(sentence-transformers fp32, 정확), 요청 시점은 onnx int8. Task 1 에서 결정(코사인 0.977, top-100 겹침 검사 통과 시).
- 공통: `--space openai|kure` (기본 settings.embed_space). 대상 선택 조건(`embedding is null`)과 저장 컬럼(`embedding`/`embedding_k`)을 공간에 따라. 회사 벡터 합성은 이력 공고의 같은 공간 컬럼을 읽는다.
- 워크플로: `daily-sync.yml`·`hourly-sync.yml` 의 임베딩 스텝에 `EMBED_SPACE: ${{ vars.EMBED_SPACE || 'openai' }}` 환경변수(리포 Variables 로 전환 제어). kure 일 때 모델 다운로드가 매 실행 ~30초·560MB — `actions/cache` 로 `~/.cache/kure-v1-int8` 캐시.
- 검증: `--space kure --limit 20` 로 bid_notices 20건 `embedding_k` 채워지고 차원 1024. 커밋.

### Task 4: 백필 (노트북 GPU) + 인덱스

**Files:** Create `docs/recommender/scripts/backfill_kure.py`(torch env)
- 대상: 진행 중 + 마감 90일 이내 공고(`bid_clse_date >= current_date - 90`), 회사 전체(업종 텍스트 있는 것), 진행 중 사전규격·발주계획. 텍스트는 운영 빌더 함수 import(`PYTHONPATH=backend`). GPU fp16, batch 64, `embedding_k` 로 UPDATE (psycopg, 1,000행 단위 `executemany`).
- 회사 벡터는 `compute_company_vectors --space kure --limit 200000` 를 **백필 뒤** 실행(이력 공고의 `embedding_k` 가 있어야 함 → 공고 백필을 먼저, 마감 90일 이내 + 회사 이력 공고 전부 포함하도록 이력 공고 키를 별도 조회해 추가).
- 끝나면 0045-b(인덱스 생성 SQL)를 Dashboard 에서. 행 수·null 수 보고.

### Task 5: 요청 경로 + 프론트

**Files:** Modify `app/services/recommend.py`, `app/services/viz.py`, `frontend/src/lib/*`(RPC 2곳)
- `recommend.py`: RPC 이름을 `settings.embed_space` 에 따라 `match_bid_notices`/`_k`, `match_pre_specs`/`_k`, `match_order_plans`/`_k`. 회사 벡터 읽는 컬럼 `embedding`/`embedding_k`. 질의 임베딩 3곳(910·980·989)은 `embedding.embed_texts` 스위치로 이미 공간을 따른다. `_fetch_result_embeddings`(MMR 용) 컬럼도.
- `viz.py`(임베딩 시각화 앵커): 같은 스위치.
- 프론트: 회사 페이지의 `rpc("match_bid_notices")`·`rpc("similar_notice_awardees")` 와 읽는 컬럼을 `NEXT_PUBLIC_EMBED_SPACE` 로 분기(기본 openai).
- Railway: `EMBED_SPACE=kure` 넣기 전까지 기존 동작. 메모리: 모델 상주 ~0.7GB — 첫 요청 지연을 피하려면 `main.py` startup 에서 `_session()` 워밍(설정이 kure 일 때만).
- 검증: 로컬에서 `EMBED_SPACE=kure` 로 회사 추천·키워드 추천 호출, Server-Timing 에 임베딩 구간 추가(`embed_query`), 1회 지연 측정.

### Task 6: 하네스 `--space`

`jobs/evaluate_recommender.py`: `--space kure` 면 `embedding_k` 컬럼 + 로컬 ONNX 임베딩(업종 텍스트)으로 재생. (`--embeddings npz` 는 실험용으로 유지.) 검증: `--as-of 2026-08-01 --space kure` 가 실험(`emb-kure-0801`)과 ±0.01 안.

### Task 7: 점수표 재보정 (KURE 분포)

`--space kure --dump-features` 3시점 → `jobs.fit_score_weights` → 표 후보 → held-out 비교 → 채택 시 `score.py` 갱신 + `exp-2026-10-16-score-kure.md`. 운영 조건(top5) 전후.

### Task 8: 컷오버

- 리포 Variables `EMBED_SPACE=kure`(Actions), Railway `EMBED_SPACE=kure`, Vercel `NEXT_PUBLIC_EMBED_SPACE=kure`. 배포 후 운영 추천 호출 확인, Sentry 24h.
- changelog.md 항목 추가. 1주 뒤 문제 없으면 OpenAI 임베딩 스텝 제거·옛 컬럼은 유지(롤백용, 디스크 여유).
- **OpenAI 스텝을 끊기 전에** 프론트에서 옛 `embedding` 컬럼 유무로 판단하는 두 곳을 `embedding_k` 로 바꿀 것: 회사 브라우즈/사이트맵의 '깡통 회사' 필터(`.not("embedding","is",null)`)와 `notice.ts` 의 `has_embedding`. 안 바꾸면 신규 회사·공고가 전부 '벡터 없음'으로 사이트맵에서 빠진다(Task 5 보고).
- 협업 경로(`collaborative.fetch_peer_institutions` → `match_companies`)는 현재 꺼져 있음. 되살릴 때 `_k` 분기 필요.
