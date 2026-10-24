# 첨부문서 파이프라인 보강 계획 (읽기는 전부, 선별은 쓰는 단계에서)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** 첨부문서를 빠짐없이 읽어 저장하고(xlsx·zip 포함, 개수 한도 없음, 중복 제거), 마감 지난 공고의 문서 텍스트를 비워 저장 증가를 멈추고, 인사이트 커버리지를 매일 100% 로 유지한다.

**근거(2026-10-15 실측, 최근 60일):** 건너뛴 파일 2.7만 개 중 xlsx 1.5만(물품 규격서 74%가 xlsx)·zip 4.7천. 공고당 지원 파일 6개 이상이 8%(한도 5). 문서 텍스트 1.6GB, 매달 +1GB. 1.2만 자 컷은 핵심 절을 99% 포함하므로 유지.

**Architecture:** `doc_extract.py` 에 xlsx·zip 추출 추가. `extract_bid_documents.py` 는 한도 제거·텍스트 해시 중복 제거·zip 전개·`--reprocess-skipped`. 새 잡 `purge_expired_documents.py` 가 마감+7일 지난 공고의 text 를 비운다(status='purged'). `summarize_bid_documents.py` 는 `--limit` 이 500 을 넘으면 500 단위로 여러 배치를 제출한다.

**Tech:** openpyxl(read_only) 추가, zipfile(stdlib). DB 스키마 변경 없음(seq 정수 규칙으로 zip 멤버 표현).

---

### Task 1: doc_extract — xlsx·zip 지원

**Files:** Modify `backend/app/services/doc_extract.py`, `backend/pyproject.toml`(`uv add openpyxl`)

- [ ] **Step 1: 상수·함수 추가**

`SUPPORTED_EXTS = ("hwp", "hwpx", "pdf")` → `SUPPORTED_EXTS = ("hwp", "hwpx", "pdf", "xlsx")`, 그리고 `ARCHIVE_EXTS = ("zip",)`.

```python
def extract_xlsx(data: bytes, max_rows_per_sheet: int = 2000) -> str:
    """규격서·내역서 xlsx → 시트별 텍스트. 셀은 탭, 행은 줄바꿈, 빈 셀·빈 행 생략. 수식은 값으로."""
    import openpyxl  # lazy — hwp/pdf 만 쓰는 경로의 import 비용 회피

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts: list[str] = []
    for ws in wb.worksheets:
        lines: list[str] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows_per_sheet:
                lines.append(f"... (이하 {ws.max_row - max_rows_per_sheet}행 생략)")
                break
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                lines.append("\t".join(cells))
        if lines:
            parts.append(f"[시트: {ws.title}]\n" + "\n".join(lines))
    wb.close()
    return "\n\n".join(parts)


def iter_zip_members(data: bytes) -> list[tuple[str, bytes]]:
    """zip 안의 지원 형식 파일만 (이름, 바이트) 로. 중첩 zip 은 한 단계만. 20MB 초과 멤버·암호 zip 은 건너뜀."""
    out: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.file_size > 20 * 1024 * 1024:
                continue
            name = _decode_zip_name(info)
            ext = ext_of(name)
            if ext in SUPPORTED_EXTS:
                try:
                    out.append((name, zf.read(info)))
                except RuntimeError:  # 암호
                    continue
    return out


def _decode_zip_name(info: "zipfile.ZipInfo") -> str:
    """한글 파일명: UTF-8 플래그 없으면 cp949 로 복원 (나라장터 zip 대부분)."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except Exception:
        return info.filename
```
`extract_text` 에 `if fmt == "xlsx": return extract_xlsx(data)` 추가. `sniff_format` 은 zip 매직(`PK\x03\x04`)이 hwpx 와 겹치므로 **xlsx 판별은 확장자 우선**: `extract_text` 맨 앞에 `if ext == "xlsx": return extract_xlsx(data)`.

- [ ] **Step 2: 자체 점검** — `uv run python -c` 로 openpyxl 로 만든 2시트 워크북 바이트를 `extract_xlsx` 에 넣어 `[시트:` 가 2번 나오는지, 빈 셀이 생략되는지 assert. zip 은 `zipfile` 로 한글 파일명 멤버(cp949 로 인코딩) 하나 넣어 `iter_zip_members` 가 이름을 복원하는지 assert.

- [ ] **Step 3: 커밋** `feat(doc_extract): xlsx(규격서·내역서)·zip 멤버 추출`

### Task 2: extract 잡 — 한도 제거·중복 제거·zip 전개·skipped 재처리

**Files:** Modify `backend/jobs/extract_bid_documents.py`

- [ ] **Step 1: 선택 규칙**

`MAX_FILES_PER_NOTICE` 삭제. `_pick_files` 는 **지원 형식 + 아카이브 전부**를 우선순위·seq 순으로 반환하고, 나머지(docx·xls·hwp 아닌 미지원)만 `skipped`. 즉:
```python
def _pick_files(attachments):
    chosen = [a for a in attachments if ext_of(a.get("name")) in SUPPORTED_EXTS + ARCHIVE_EXTS]
    chosen.sort(key=lambda a: (_priority(a.get("name")), a.get("seq", 0)))
    chosen_seqs = {a["seq"] for a in chosen}
    rest = [a for a in attachments if a.get("seq") not in chosen_seqs]
    return chosen, rest
```

- [ ] **Step 2: process_notice — 중복 제거 + zip 전개**

같은 공고 안에서 텍스트 SHA-1 이 같은 파일(공고문 hwp/pdf 쌍)은 두 번째부터 `status='duplicate'`, text 없음, `error='same as seq N'`. 해시는 공백 정규화 후(`" ".join(text.split())`) 앞 20,000자로.
zip 은 멤버마다 행 하나: `seq = parent_seq * 100 + k` (k = 1..99, 멤버 100개 초과는 버림), `file_name = f"{zip이름}/{멤버이름}"`, `url = 부모 url`, `ext = 멤버 ext`. zip 자체 행은 `status='archive'`, `error=f'{len(members)} members'`.
구현 뼈대:
```python
def _store(row, text, seen_hashes):
    if len(text) > MAX_TEXT_CHARS: text = text[:MAX_TEXT_CHARS]
    if not text.strip(): row["status"] = "empty"; return
    h = hashlib.sha1(" ".join(text.split())[:20000].encode()).hexdigest()
    if h in seen_hashes:
        row.update(status="duplicate", error=f"same as seq {seen_hashes[h]}"); return
    seen_hashes[h] = row["seq"]
    row.update(status="ok", text=text, char_count=len(text))
```
`process_notice` 루프에서 `ext in ARCHIVE_EXTS` 면 `iter_zip_members` 로 멤버를 돌며 `_store` (멤버당 `extract_text`), 아니면 기존 흐름에 `_store` 적용. 다운로드 지연은 **파일당**(멤버는 지연 없음).

- [ ] **Step 3: `--reprocess-skipped N`**

옵션이 주어지면 RPC 대신 직접 조회: `bid_notice_documents` 에서 `status='skipped' and ext in ('xlsx','zip')` 이고 공고가 진행 중(`bid_notices.bid_clse_date >= current_date`)인 행을 최대 N건(공고 단위로 묶어) 가져와 그 파일들만 다시 처리(기존 행은 upsert 로 덮어씀, pkey 동일). supabase 클라이언트로는 join 이 번거로우니 `sb.rpc` 대신 두 번 조회(진행 중 공고 no 집합 → skipped 행 필터)로 구현해도 된다. 한 번에 최대 2,000행.

- [ ] **Step 4: 검증** — `uv run python -m jobs.extract_bid_documents --limit 5` 가 돌고, 결과 행에 `duplicate`/`archive`/멤버 행(seq ≥ 100)이 보이는지 DB 에서 확인. `--reprocess-skipped 20` 으로 xlsx 가 `ok` 로 바뀌는지 확인(`char_count > 0`).

- [ ] **Step 5: 커밋** `feat(jobs): 첨부 추출 — 개수 한도 제거·텍스트 중복 제거·zip 전개·xlsx·skipped 재처리`

### Task 3: 마감 지난 문서 텍스트 비우기

**Files:** Create `backend/jobs/purge_expired_documents.py`, Modify `.github/workflows/daily-sync.yml`(sync 잡 끝에 스텝 1개, `continue-on-error: true`)

```python
"""마감+7일 지난 공고의 첨부문서 텍스트를 비운다 (status='purged'). 인사이트는 이미 뽑혀 있고 임베딩은 문서를 안 쓴다.
문서 텍스트 1.6GB 가 매달 1GB 씩 늘던 것을 진행 중 공고분(~0.4GB)으로 고정한다. 실행: uv run python -m jobs.purge_expired_documents [--grace-days 7] [--batch 2000]"""
```
psycopg 직결(`DATABASE_URL`, backfill_companies_basic 과 같은 방식). 배치 UPDATE:
```sql
with t as (
  select d.bid_ntce_no, d.bid_ntce_ord, d.seq from bid_notice_documents d
  join bid_notices b using (bid_ntce_no, bid_ntce_ord)
  where d.text is not null and b.bid_clse_date < current_date - %s
  limit %s)
update bid_notice_documents d set text = null, status = 'purged'
from t where d.bid_ntce_no = t.bid_ntce_no and d.bid_ntce_ord = t.bid_ntce_ord and d.seq = t.seq
```
반복해서 0행이 될 때까지, 배치마다 commit, 출력에 누적 건수. `statement_timeout` 5분. 첫 실행은 수십만 행이라 10~20분. daily-sync 에는 `회사 벡터 재계산` 처럼 별도 스텝으로 sync 잡 마지막에.

- [ ] 검증: `--batch 500` 으로 한 번 돌려 500행 purged 확인 후 전량 실행. 커밋 `feat(jobs): 마감 지난 공고 문서 텍스트 비우기 (purge_expired_documents) + daily-sync 스텝`

### Task 4: summarize — 여러 배치 제출

**Files:** Modify `backend/jobs/summarize_bid_documents.py`

`run(limit)` 에서 `submit` 을 `while remaining > 0` 로 반복(배치당 `min(500, remaining)`), 제출 0건이면 중단. `--limit` 도움말을 "이번 실행 제출 상한(500 단위 배치 여러 개)" 으로. 검증: `--limit 0` 수거만 정상. 커밋 `feat(insights): --limit 이 500 을 넘으면 배치 여러 개 제출`.

### Task 5: 문서

`docs/recommender/exp-2026-10-15-insights-model.md` 끝의 후속 항목 중 완료된 것 체크, `README.md` §8 잡 목록에 `purge_expired_documents` 한 줄. 커밋.
