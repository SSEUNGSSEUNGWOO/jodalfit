"""입찰공고 첨부파일 다운로드 → 텍스트 추출 → bid_notice_documents 저장 잡.

대상: bid_notices.attachments가 있고 아직 문서 row가 없는 **진행 중** 공고
(RPC next_bid_notices_for_documents, 0021). 최신 공고부터.

공고당 최대 MAX_FILES_PER_NOTICE개, 제안요청서·과업지시서 계열 파일을 우선.
hwp/hwpx/pdf만 추출하고 나머지(zip, xlsx 등)는 skipped로 기록해 재처리 안 함.
파일 원본은 저장하지 않는다.

실행:
    cd backend
    uv run python -m jobs.extract_bid_documents --limit 200
"""

from __future__ import annotations

import argparse
import logging
import re
import time

import httpx

from app.services.doc_extract import (
    SUPPORTED_EXTS,
    UnsupportedDocument,
    ext_of,
    extract_text,
)
from app.services.supabase_client import get_admin_client, upsert_rows
from jobs._common import log_ingest_finish, log_ingest_start

logging.getLogger("pypdf").setLevel(logging.ERROR)  # "Ignoring wrong pointing object" 경고 소음 차단

JOB_NAME = "extract_bid_documents"
MAX_FILES_PER_NOTICE = 5
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
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


def _pick_files(attachments: list[dict]) -> list[dict]:
    """지원 확장자 파일을 우선순위·seq 순으로 정렬해 앞에서 MAX개 선택.
    나머지(미지원 포함)는 skipped 기록용으로 함께 반환."""
    supported = [a for a in attachments if ext_of(a.get("name")) in SUPPORTED_EXTS]
    supported.sort(key=lambda a: (_priority(a.get("name")), a.get("seq", 0)))
    chosen = supported[:MAX_FILES_PER_NOTICE]
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


def process_notice(client: httpx.Client, no: str, ord_: str, attachments: list[dict]) -> list[dict]:
    rows: list[dict] = []
    chosen, rest = _pick_files(attachments)
    base = {"bid_ntce_no": no, "bid_ntce_ord": ord_}

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
            text = extract_text(data, ext)
            if len(text) > MAX_TEXT_CHARS:
                text = text[:MAX_TEXT_CHARS]
            if not text.strip():
                row["status"] = "empty"
            else:
                row.update(status="ok", text=text, char_count=len(text))
        except UnsupportedDocument as e:
            row.update(status="unsupported", error=str(e)[:500])
        except Exception as e:  # 다운로드/파싱 실패 — 공고 하나 때문에 잡 전체가 죽지 않게
            row.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
        rows.append(row)
        time.sleep(DOWNLOAD_DELAY_SEC)
    return rows


def run(limit: int = 200) -> None:
    run_id = log_ingest_start(JOB_NAME, {"limit": limit})
    sb = get_admin_client()
    targets = sb.rpc("next_bid_notices_for_documents", {"p_limit": limit}).execute().data or []
    print(f"[{JOB_NAME}] {len(targets)} notices to process")

    stats: dict[str, int] = {}
    notices_done = 0
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers={"User-Agent": "Mozilla/5.0 (jodalfit bid-document-fetcher)"},
        ) as client:
            for i, t in enumerate(targets, 1):
                rows = process_notice(client, t["bid_ntce_no"], t["bid_ntce_ord"], t["attachments"] or [])
                if rows:
                    upsert_rows("bid_notice_documents", rows, on_conflict="bid_ntce_no,bid_ntce_ord,seq")
                for r in rows:
                    stats[r["status"]] = stats.get(r["status"], 0) + 1
                notices_done += 1
                if i % 20 == 0:
                    print(f"  {i}/{len(targets)} notices, files={stats}")
        log_ingest_finish(run_id, "success", rows_inserted=sum(stats.values()), rows_failed=stats.get("error", 0))
        print(f"[{JOB_NAME}] done. notices={notices_done} files={stats}")
    except Exception as e:
        log_ingest_finish(run_id, "failed", rows_inserted=sum(stats.values()), error_msg=str(e))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="처리할 공고 수")
    args = parser.parse_args()
    run(args.limit)
