"""IndexNow 핑 — 새로 생기거나 바뀐 공고·회사 페이지 URL 을 검색엔진에 직접 알린다.

IndexNow(https://www.indexnow.org)는 Bing·네이버(2023-07 부터)·Yandex 가 받는 규격이다. 구글은 받지 않는다.
한 엔드포인트(api.indexnow.org)에 보내면 참여 엔진끼리 공유한다. 하루 10,000 URL, 요청당 10,000 URL.

왜: 공고 페이지는 수명이 2~4주라 색인이 느리면 마감 뒤에 검색에 뜬다. 네이버는 하루 3천 페이지쯤 수집한다(2026-10-11 성적표).
매시 수집(hourly-sync.yml) 뒤 새 공고 URL 을 바로 보내면 살아 있는 동안 검색에 걸린다.

키: 사이트가 `https://jodalfit.co.kr/<key>.txt`(내용 = key) 를 서빙해야 한다 — frontend/public/<key>.txt. 키 자체는 비밀이 아니다
(파일이 공개돼야 검증된다). 기본 키는 아래 DEFAULT_KEY, 환경변수 INDEXNOW_KEY 로 바꿀 수 있다(Bing 웹마스터가 준 키를 쓰려면
그 키로 public 파일도 바꾼다).

실행:
    cd backend
    uv run python -m jobs.ping_indexnow --hours 2            # 최근 2시간 갱신분 (매시 잡)
    uv run python -m jobs.ping_indexnow --hours 24 --dry-run # 보낼 URL 만 출력
    uv run python -m jobs.ping_indexnow --url https://jodalfit.co.kr/ --url https://jodalfit.co.kr/faq   # 지정 URL 만
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

from app.services.supabase_client import get_admin_client
from jobs._common import log_ingest_finish, log_ingest_start

JOB_NAME = "ping_indexnow"
HOST = "jodalfit.co.kr"
BASE = f"https://{HOST}"
DEFAULT_KEY = "a9293d4d5aa38d096ae1e3d534e78bf7"   # frontend/public/a9293d4d5aa38d096ae1e3d534e78bf7.txt
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_PER_REQUEST = 10_000


def changed_urls(client, since: datetime, limit: int) -> list[str]:
    """최근 바뀐 공고(마감 전·벡터 있음, 공고번호당 하나)와 회사(벡터 있음·비공개 아님·10자리) 페이지. 공고 먼저."""
    today = datetime.now(timezone.utc).date().isoformat()
    urls: list[str] = []
    seen: set[str] = set()
    rows = (
        client.table("bid_notices").select("bid_ntce_no,updated_at")
        .gte("updated_at", since.isoformat()).gte("bid_clse_date", today).not_.is_("embedding_k", "null")
        .order("updated_at", desc=True).limit(limit).execute().data or []
    )
    for r in rows:
        no = r["bid_ntce_no"]
        if no and no not in seen:
            seen.add(no)
            urls.append(f"{BASE}/notices/{no}")
    rows = (
        client.table("companies").select("bizrno_norm,updated_at")
        .gte("updated_at", since.isoformat()).not_.is_("embedding_k", "null").is_("optout_at", "null")
        .order("updated_at", desc=True).limit(limit).execute().data or []
    )
    for r in rows:
        norm = r.get("bizrno_norm") or ""
        if len(norm) == 10 and norm.isdigit() and norm not in seen:
            seen.add(norm)
            urls.append(f"{BASE}/companies/{norm}")
    return urls[:limit]


def ping(urls: list[str], key: str, endpoint: str = ENDPOINT) -> list[tuple[int, int]]:
    """요청당 10,000 건씩 POST. [(보낸 수, HTTP 상태)]. 200/202 가 정상."""
    out: list[tuple[int, int]] = []
    with httpx.Client(timeout=30) as http:
        for i in range(0, len(urls), MAX_PER_REQUEST):
            chunk = urls[i : i + MAX_PER_REQUEST]
            body = {"host": HOST, "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": chunk}
            res = http.post(endpoint, json=body, headers={"Content-Type": "application/json; charset=utf-8"})
            out.append((len(chunk), res.status_code))
            if res.status_code not in (200, 202):
                print(f"[{JOB_NAME}] {res.status_code}: {res.text[:200]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=2.0, help="이 시간 안에 갱신된 공고·회사 (기본 2 — 매시 잡 + 여유)")
    ap.add_argument("--limit", type=int, default=MAX_PER_REQUEST, help="최대 URL 수 (IndexNow 일일 한도 10,000)")
    ap.add_argument("--url", action="append", default=[], help="갱신분 대신 이 URL 만 (여러 번)")
    ap.add_argument("--endpoint", default=os.getenv("INDEXNOW_ENDPOINT", ENDPOINT))
    ap.add_argument("--dry-run", action="store_true", help="보낼 URL 만 출력")
    args = ap.parse_args()
    key = os.getenv("INDEXNOW_KEY", DEFAULT_KEY)

    if args.url:
        urls = args.url
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        urls = changed_urls(get_admin_client(), since, args.limit)
    print(f"[{JOB_NAME}] {len(urls)} urls" + (" (dry-run)" if args.dry_run else ""))
    for u in urls[:10]:
        print("  ", u)
    if len(urls) > 10:
        print(f"   … +{len(urls) - 10}")
    if args.dry_run or not urls:
        return 0

    run_id = log_ingest_start(JOB_NAME, {"hours": args.hours, "urls": len(urls), "endpoint": args.endpoint})
    try:
        results = ping(urls, key, args.endpoint)
    except Exception as e:  # 네트워크 등 — 실패로 남기고 다음 시간에 다시
        log_ingest_finish(run_id, "error", error_msg=str(e)[:500])
        print(f"[{JOB_NAME}] failed: {e}")
        return 1
    sent = sum(n for n, code in results if code in (200, 202))
    failed = sum(n for n, code in results if code not in (200, 202))
    log_ingest_finish(run_id, "ok" if not failed else "error", rows_inserted=sent, rows_failed=failed,
                      error_msg=None if not failed else f"http {[c for _, c in results]}")
    print(f"[{JOB_NAME}] sent {sent}, failed {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
