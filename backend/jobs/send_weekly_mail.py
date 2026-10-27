"""저장한 회사의 새 공고 주간 메일 — 매주 월요일 08:00 KST (.github/workflows/weekly-mail.yml).

가입할 이유가 없는 것이 깔때기의 가장 큰 구멍이었다(2026-10-27). PRODUCT.md 의 무료 범위 "주간 TOP5" 를 이 잡이 맡는다.

받는 사람: 메일 인증을 마친 회원 중 가입 때 "[선택] 알림 메일 수신 동의"(0052 user_consents.marketing_opt_in) 를 켰고
          검토함에 저장한 회사(saved_companies)가 하나 이상인 사람. 6일 안에 이미 보냈으면(0063 weekly_mail_log) 건너뛴다.
내용:     회사마다 recommend()(운영과 같은 v2 파이프라인)를 돌려 최근 N일(기본 7)에 등록된 공고 중 상위 5건. 새 공고가 한 건도
          없는 회사는 빼고, 보낼 회사가 없으면 메일 자체를 보내지 않는다(빈 메일은 수신 거부를 부른다).
그만 받기: 메일 하단 링크 → /mail/weekly?u=<user_id>&t=<HMAC>. 토큰은 INTERNAL_API_TOKEN 으로 만든 HMAC-SHA256 앞 32자리
          (frontend/src/lib/mail-link.ts 와 같은 식). 링크를 누르면 확인 버튼 한 번 더(메일 보안 스캐너가 GET 만으로 해지하지 않게).

사용: cd backend && uv run python -m jobs.send_weekly_mail [--dry-run] [--days 7] [--out DIR]
      시험 발송: --to you@example.com --bizrno 1248177731 [--bizrno ...]   (기록 안 남김, 동의 여부 무관)
필요 환경: DATABASE_URL(auth.users 읽기), SUPABASE_*, RESEND_API_KEY, INTERNAL_API_TOKEN, EMBED_SPACE(벡터 없는 회사의 즉석 임베딩)
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv

from app.core.config import get_settings

load_dotenv()  # DATABASE_URL 은 Settings 에 없다 — purge_expired_documents 와 같은 방식

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("send_weekly_mail")

SITE = "https://jodalfit.co.kr"
UTM = "utm_source=weekly&utm_medium=email"
TOP_N = 5
FROM = "조달핏 <noreply@jodalfit.co.kr>"


def mail_token(user_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()[:32]


def _won(v) -> str:
    if v is None:
        return "—"
    v = int(v)
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v // 10_000:,}만"
    return f"{v:,}원"


def _dleft(d: str | None, today: date) -> str:
    if not d:
        return "—"
    n = (date.fromisoformat(d[:10]) - today).days
    return f"D-{n}" if n >= 0 else "마감"


def pick_new(results: list[dict], since: date) -> list[dict]:
    """최근 등록 공고만, 추천 순서 그대로 상위 TOP_N. 등록일이 없는 행은 새 공고로 보지 않는다."""
    out = [r for r in results if (r.get("bid_ntce_date") or "") >= since.isoformat()]
    return out[:TOP_N]


def render(blocks: list[dict], today: date, unsubscribe: str | None) -> tuple[str, str, str]:
    """(subject, html, text). blocks = [{corp_nm, bizrno_norm, rows:[...]}]."""
    n_rows = sum(len(b["rows"]) for b in blocks)
    first = blocks[0]["corp_nm"]
    more = f" 외 {len(blocks) - 1}곳" if len(blocks) > 1 else ""
    subject = f"[조달핏] 이번 주 검토할 공고 — {first}{more} · {n_rows}건"

    h: list[str] = []
    t: list[str] = []
    h.append('<div style="font-family:Pretendard,-apple-system,\'Segoe UI\',Roboto,\'Noto Sans KR\',sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:24px 16px;line-height:1.6">')
    h.append('<p style="margin:0 0 4px;font-size:13px;color:#6b6560">조달핏 · 저장한 회사의 새 공고</p>')
    h.append(f'<h1 style="margin:0 0 18px;font-size:20px;font-weight:700;letter-spacing:-0.02em">이번 주 검토할 공고 {n_rows}건</h1>')
    t.append(f"조달핏 · 이번 주 검토할 공고 {n_rows}건\n")
    for b in blocks:
        link = f"{SITE}/recommendations?company={b['bizrno_norm']}&{UTM}"
        h.append(f'<h2 style="margin:22px 0 6px;font-size:15px;font-weight:700;border-bottom:1px solid #1a1a1a;padding-bottom:6px">{html.escape(b["corp_nm"])} <a href="{link}" style="font-weight:500;font-size:12.5px;color:#6b6560">추천 전체 보기 →</a></h2>')
        t.append(f"\n■ {b['corp_nm']}  ({link})")
        for r in b["rows"]:
            no = r.get("bid_ntce_no")
            nl = f"{SITE}/notices/{no}?{UTM}"
            org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "—"
            dl = _dleft(r.get("bid_clse_date"), today)
            h.append(
                '<div style="padding:10px 0;border-bottom:1px solid #e6e2dc">'
                f'<a href="{nl}" style="color:#1a1a1a;font-weight:600;text-decoration:none;font-size:15px">{html.escape(r.get("bid_ntce_nm") or "")}</a>'
                f'<div style="font-size:12.5px;color:#6b6560;margin-top:2px">{html.escape(org)} · 마감 <b style="color:#b85510">{dl}</b> · 추정가 {_won(r.get("presmpt_prce"))}</div>'
                "</div>"
            )
            t.append(f"- {r.get('bid_ntce_nm')}  | {org} | 마감 {dl} | 추정가 {_won(r.get('presmpt_prce'))}\n  {nl}")
    h.append('<p style="margin:22px 0 0;font-size:12.5px;color:#6b6560;line-height:1.7">추천은 검토 순서이며 낙찰을 예측하지 않습니다. 최근 7일에 등록된 공고 중 각 회사의 등록업종·공급물품·수주 이력에 맞는 순서로 골랐습니다.<br>'
             f'저장한 회사를 바꾸려면 <a href="{SITE}/saved?{UTM}" style="color:#1a1a1a">검토함</a>에서 합니다.')
    if unsubscribe:
        h.append(f'<br><a href="{unsubscribe}" style="color:#6b6560">이 메일 그만 받기</a>')
    h.append("</p></div>")
    t.append("\n추천은 검토 순서이며 낙찰을 예측하지 않습니다. 저장한 회사를 바꾸려면 검토함: " + f"{SITE}/saved")
    if unsubscribe:
        t.append(f"이 메일 그만 받기: {unsubscribe}")
    return subject, "".join(h), "\n".join(t)


def build_blocks(bizrnos: list[str], since: date) -> list[dict]:
    from app.services.recommend import recommend  # 무거운 import 는 필요할 때

    blocks: list[dict] = []
    for b in bizrnos:
        try:
            d = recommend(b, limit=20, candidate_pool=200, mode="company", algorithm="v2")
        except Exception as e:
            logger.warning("recommend 실패 %s: %s", b, e)
            continue
        co = d.get("company")
        if not co or d.get("error"):
            continue  # 비공개 요청·제재·벡터 없음 — 메일에 싣지 않는다
        rows = pick_new(d.get("results") or [], since)
        if rows:
            blocks.append({"corp_nm": co["corp_nm"], "bizrno_norm": b, "rows": rows})
    return blocks


def send(api_key: str, to: str, subject: str, html_body: str, text: str) -> str | None:
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": FROM, "to": [to], "subject": subject, "html": html_body, "text": text},
        timeout=20,
    )
    if r.status_code >= 400:
        logger.warning("resend 실패 %s: %s %s", to, r.status_code, r.text[:200])
        return None
    return r.json().get("id")


def recipients(conn) -> list[tuple[str, str, list[str]]]:
    rows = conn.execute(
        """
        select u.id::text, u.email, array_agg(distinct s.bizrno_norm order by s.bizrno_norm)
          from auth.users u
          join public.user_consents c on c.user_id = u.id and c.marketing_opt_in
          join public.saved_companies s on s.user_id = u.id
         where u.email_confirmed_at is not null and u.deleted_at is null and u.email is not null
           and not exists (select 1 from public.weekly_mail_log l
                            where l.user_id = u.id and l.sent_at > now() - interval '6 days')
         group by u.id, u.email
         order by u.email
        """
    ).fetchall()
    return [(r[0], r[1], list(r[2])) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 대상·건수만 출력")
    ap.add_argument("--days", type=int, default=7, help="최근 N일 등록 공고")
    ap.add_argument("--out", help="렌더한 HTML 을 이 폴더에 저장(미리보기)")
    ap.add_argument("--to", help="시험 발송 주소(--bizrno 와 함께, 기록 안 남김)")
    ap.add_argument("--bizrno", action="append", help="시험 발송 회사(10자리), 여러 번")
    a = ap.parse_args()

    s = get_settings()
    today = datetime.now(timezone(timedelta(hours=9))).date()
    since = today - timedelta(days=a.days)
    out = Path(a.out) if a.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    if a.to:
        if not a.bizrno:
            print("--to 에는 --bizrno 가 필요합니다", file=sys.stderr)
            return 2
        blocks = build_blocks([b.replace("-", "") for b in a.bizrno], since)
        if not blocks:
            print("최근 등록 공고가 없어 보낼 내용이 없습니다")
            return 0
        subject, h, t = render(blocks, today, f"{SITE}/mail/weekly?u=test&t=test")
        if out:
            (out / "test.html").write_text(h, encoding="utf-8")
        if a.dry_run or not s.resend_api_key:
            print(f"[dry] {a.to}: {subject}")
            return 0
        print("sent", send(s.resend_api_key, a.to, subject, h, t), subject)
        return 0

    secret = s.internal_api_token
    if not secret:
        print("INTERNAL_API_TOKEN 이 없어 그만 받기 링크를 만들 수 없습니다", file=sys.stderr)
        return 2
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL 이 없습니다(auth.users 읽기)", file=sys.stderr)
        return 2

    sent = skipped = 0
    with psycopg.connect(url) as conn:
        targets = recipients(conn)
        logger.info("대상 %d명 (동의·인증·저장 회사 있음·6일 내 미발송)", len(targets))
        for uid, email, bizrnos in targets:
            blocks = build_blocks(bizrnos, since)
            if not blocks:
                skipped += 1
                logger.info("  %s: 새 공고 없음 — 보내지 않음 (회사 %d)", email, len(bizrnos))
                continue
            unsub = f"{SITE}/mail/weekly?u={uid}&t={mail_token(uid, secret)}"
            subject, h, t = render(blocks, today, unsub)
            n = sum(len(b["rows"]) for b in blocks)
            if out:
                (out / f"{email.replace('@', '_at_')}.html").write_text(h, encoding="utf-8")
            if a.dry_run or not s.resend_api_key:
                logger.info("  [dry] %s: %s", email, subject)
                continue
            rid = send(s.resend_api_key, email, subject, h, t)
            if rid:
                conn.execute(
                    "insert into public.weekly_mail_log (user_id, companies, notices, resend_id) values (%s, %s, %s, %s)",
                    (uid, len(blocks), n, rid),
                )
                conn.commit()
                sent += 1
                logger.info("  sent %s: %s", email, subject)
    logger.info("끝 — 보냄 %d · 새 공고 없어 건너뜀 %d", sent, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
