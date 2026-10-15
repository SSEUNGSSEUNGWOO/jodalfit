"""입찰공고 첨부파일 다운로드 → 텍스트 추출 → bid_notice_documents 저장 잡.

대상: bid_notices.attachments가 있고 아직 문서 row가 없는 **진행 중** 공고
(RPC next_bid_notices_for_documents, 0021). 최신 공고부터.

지원 형식(hwp/hwpx/pdf/xlsx) + zip 전부를 개수 한도 없이 읽는다. zip은 멤버마다 행 하나
(seq = 부모seq*100 + k). 같은 공고 안에서 텍스트가 같은 파일(공고문 hwp/pdf 쌍)은 duplicate로
기록해 텍스트를 중복 저장하지 않는다. 그 외 미지원 형식만 skipped.
파일 원본은 저장하지 않는다.

실행:
    cd backend
    uv run python -m jobs.extract_bid_documents --limit 200
    uv run python -m jobs.extract_bid_documents --reprocess-skipped 500  # 과거 xlsx·zip 재처리
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import time
from datetime import date

import httpx
from postgrest.exceptions import APIError

from app.services.doc_extract import (
    ARCHIVE_EXTS,
    SUPPORTED_EXTS,
    UnsupportedDocument,
    ext_of,
    extract_text,
    iter_zip_members,
)
from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start

logging.getLogger("pypdf").setLevel(logging.ERROR)  # "Ignoring wrong pointing object" 경고 소음 차단

JOB_NAME = "extract_bid_documents"
STATEMENT_TIMEOUT = "57014"


def _db(step: str, fn, retries: int = 3):
    """Supabase 호출 — statement timeout(57014)이면 backoff 재시도 (summarize 잡과 같은 패턴)."""
    for attempt in range(retries):
        try:
            return fn()
        except APIError as e:
            if e.code != STATEMENT_TIMEOUT or attempt == retries - 1:
                raise RuntimeError(f"[{step}] {e.code}: {e.message}") from e
            wait = 3 * (attempt + 1)
            print(f"  {step}: statement timeout, retry in {wait}s")
            time.sleep(wait)
RPC_BATCH = 500  # 한 번에 받아올 대상 공고 수 (PostgREST 1,000행 상한 아래)
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_ZIP_MEMBERS = 99  # 멤버 seq = 부모seq*100 + k (k=1..99)
MAX_REPROCESS_ROWS = 2000  # --reprocess-skipped 한 번에 가져올 행 수 상한
DOWNLOAD_DELAY_SEC = 0.3  # 나라장터 부하 완화

# 우선순위: 낮을수록 먼저. 제안요청서/과업지시서 > 공고문 > 나머지
_PRIORITY = [
    (re.compile(r"제안\s*요청|과업\s*(지시|내용|설명)|규격서|사양서|RFP", re.I), 0),
    (re.compile(r"공고"), 1),
]


def _priority(name: str | None) -> int:
    for pat, p in _PRIORITY:
        if name and pat.search(name):
            return p
    return 2


def _pick_files(attachments: list[dict]) -> tuple[list[dict], list[dict]]:
    """지원 확장자 + 아카이브 전부를 우선순위·seq 순으로. 나머지(미지원)는 skipped 기록용."""
    chosen = [a for a in attachments if ext_of(a.get("name")) in SUPPORTED_EXTS + ARCHIVE_EXTS]
    chosen.sort(key=lambda a: (_priority(a.get("name")), a.get("seq", 0)))
    chosen_seqs = {a["seq"] for a in chosen}
    rest = [a for a in attachments if a.get("seq") not in chosen_seqs]
    return chosen, rest


def _download(client: httpx.Client, url: str) -> bytes:
    with client.stream("GET", url) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "text/html" in ctype:
            raise RuntimeError(f"html response (content-type={ctype})")
        buf = bytearray()
        for chunk in resp.iter_bytes():
            buf.extend(chunk)
            if len(buf) > MAX_FILE_BYTES:
                raise RuntimeError(f"file too large (> {MAX_FILE_BYTES} bytes)")
        return bytes(buf)


def _store(row: dict, text: str, seen_hashes: dict[str, int]) -> None:
    """추출 텍스트를 행에 담는다. 같은 공고 안에서 내용이 같은 파일은 duplicate(텍스트 미저장)."""
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    if not text.strip():
        row["status"] = "empty"
        return
    h = hashlib.sha1(" ".join(text.split())[:20_000].encode()).hexdigest()
    if h in seen_hashes:
        row.update(status="duplicate", error=f"same as seq {seen_hashes[h]}")
        return
    seen_hashes[h] = row["seq"]
    row.update(status="ok", text=text, char_count=len(text))


def _extract_into(row: dict, data: bytes, seen_hashes: dict[str, int]) -> None:
    try:
        _store(row, extract_text(data, row["ext"]), seen_hashes)
    except UnsupportedDocument as e:
        row.update(status="unsupported", error=str(e)[:500])
    except Exception as e:  # 파싱 실패 — 파일 하나 때문에 잡 전체가 죽지 않게
        row.update(status="error", error=f"{type(e).__name__}: {e}"[:500])


def process_notice(client: httpx.Client, no: str, ord_: str, attachments: list[dict]) -> list[dict]:
    rows: list[dict] = []
    chosen, rest = _pick_files(attachments)
    base = {"bid_ntce_no": no, "bid_ntce_ord": ord_}
    seen_hashes: dict[str, int] = {}

    for a in rest:
        rows.append(
            {**base, "seq": a["seq"], "file_name": a.get("name"), "url": a["url"],
             "ext": ext_of(a.get("name")) or None, "status": "skipped"}
        )

    for a in chosen:
        ext = ext_of(a.get("name"))
        row = {**base, "seq": a["seq"], "file_name": a.get("name"), "url": a["url"], "ext": ext}
        try:
            data = _download(client, a["url"])
        except Exception as e:  # 다운로드 실패
            row.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
            rows.append(row)
            time.sleep(DOWNLOAD_DELAY_SEC)
            continue

        if ext in ARCHIVE_EXTS:
            try:
                members = iter_zip_members(data)
            except Exception as e:
                row.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
                members = []
            else:
                row.update(status="archive", error=f"{len(members)} members")
            rows.append(row)
            for k, (name, mdata) in enumerate(members[:MAX_ZIP_MEMBERS], 1):
                mrow = {**base, "seq": a["seq"] * 100 + k, "file_name": f"{a.get('name')}/{name}",
                        "url": a["url"], "ext": ext_of(name)}
                _extract_into(mrow, mdata, seen_hashes)
                rows.append(mrow)
        else:
            _extract_into(row, data, seen_hashes)
            rows.append(row)
        time.sleep(DOWNLOAD_DELAY_SEC)
    return rows


def _skipped_targets(sb, limit: int) -> list[tuple[str, str, list[dict]]]:
    """재처리 대상: status='skipped' 인 xlsx·zip 행 중 공고가 진행 중인 것. 공고 단위로 묶어 반환.
    PostgREST 로 join 이 번거로워 두 번 조회한다 (skipped 행 → 진행 중 공고 필터)."""
    exts = ["xlsx", *ARCHIVE_EXTS]
    skipped = _db("select_skipped", lambda: (
        sb.table("bid_notice_documents").select("bid_ntce_no,bid_ntce_ord,seq,file_name,url")
        .eq("status", "skipped").in_("ext", exts)
        .order("bid_ntce_no", desc=True).limit(min(limit, MAX_REPROCESS_ROWS)).execute().data or []
    ))
    nos = sorted({r["bid_ntce_no"] for r in skipped})
    live: set[str] = set()
    today = date.today().isoformat()
    for i in range(0, len(nos), 300):
        chunk = nos[i:i + 300]
        live |= {r["bid_ntce_no"] for r in _db("select_live", lambda c=chunk: (
            sb.table("bid_notices").select("bid_ntce_no")
            .in_("bid_ntce_no", c).gte("bid_clse_date", today).execute().data or []
        ))}
    grouped: dict[tuple[str, str], list[dict]] = {}
    for r in skipped:
        if r["bid_ntce_no"] in live:
            grouped.setdefault((r["bid_ntce_no"], r["bid_ntce_ord"]), []).append(
                {"seq": r["seq"], "name": r["file_name"], "url": r["url"]}
            )
    return [(no, ord_, atts) for (no, ord_), atts in grouped.items()]


def run(limit: int = 200, reprocess_skipped: int = 0) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit, "reprocess_skipped": reprocess_skipped})
    sb = get_admin_client()
    print(f"[{JOB_NAME}] " + (f"reprocess up to {reprocess_skipped} skipped files"
                              if reprocess_skipped else f"up to {limit} notices"))

    stats: dict[str, int] = {}
    notices_done = 0

    def handle(no: str, ord_: str, attachments: list[dict]) -> None:
        nonlocal notices_done
        rows = process_notice(client, no, ord_, attachments)
        if rows:
            _db("upsert_docs", lambda r=rows: upsert_rows(
                "bid_notice_documents", r, on_conflict="bid_ntce_no,bid_ntce_ord,seq"
            ))
        for r in rows:
            stats[r["status"]] = stats.get(r["status"], 0) + 1
        notices_done += 1
        if notices_done % 50 == 0:
            print(f"  {notices_done} notices, files={stats}")

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers={"User-Agent": "Mozilla/5.0 (jodalfit bid-document-fetcher)"},
        ) as client:
            if reprocess_skipped:
                targets = _skipped_targets(sb, reprocess_skipped)
                print(f"  {len(targets)} notices with skipped xlsx/zip (진행 중 공고만)")
                for no, ord_, atts in targets:
                    handle(no, ord_, atts)
            else:
                # PostgREST 응답은 1,000행 상한 → 처리한 공고는 RPC 대상에서 빠지므로 배치로 반복
                while notices_done < limit:
                    batch = min(RPC_BATCH, limit - notices_done)
                    targets = _db("rpc_next", lambda b=batch: (
                        sb.rpc("next_bid_notices_for_documents", {"p_limit": b}).execute().data or []
                    ))
                    if not targets:
                        break
                    for t in targets:
                        handle(t["bid_ntce_no"], t["bid_ntce_ord"], t["attachments"] or [])
        log_ingest_finish(run_id, "success", rows_inserted=sum(stats.values()), rows_failed=stats.get("error", 0))
        print(f"[{JOB_NAME}] done. notices={notices_done} files={stats}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=sum(stats.values()), error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="처리할 공고 수")
    parser.add_argument("--reprocess-skipped", type=int, default=0,
                        help=f"skipped 로 기록된 xlsx·zip 을 최대 N행 재처리 (최대 {MAX_REPROCESS_ROWS}, --limit 무시)")
    args = parser.parse_args()
    run(args.limit, args.reprocess_skipped)
