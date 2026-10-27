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


def pick_new(results: list[dict], since: date) -> list[dict]:
    """최근 등록 공고만, 추천 순서 그대로 상위 TOP_N. 등록일이 없는 행은 새 공고로 보지 않는다."""
    out = [r for r in results if (r.get("bid_ntce_date") or "") >= since.isoformat()]
    return out[:TOP_N]


FONT = "Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif"
C = {"paper": "#faf9f7", "panel": "#ffffff", "hair": "#e6e4df", "rule": "#ececea", "ink": "#141414", "g": "#55554f", "mute": "#737370", "orange": "#f97316", "oink": "#b85510"}
DOW = "월화수목금토일"


def render(blocks: list[dict], today: date, unsubscribe: str | None) -> tuple[str, str, str]:
    """(subject, html, text). blocks = [{corp_nm, bizrno_norm, rows:[...]}].

    사이트와 같은 재료로(docs/design/README.md): 종이 위 흰 판, 헤어라인, 먹 글자, 주황은 선(회사 머리의 괘선·D-day 글자)뿐.
    메일 클라이언트용으로 table 과 인라인 스타일만 쓴다. 로고는 사이트의 apple-icon(PNG) — Gmail 은 SVG 를 막는다.
    """
    n_rows = sum(len(b["rows"]) for b in blocks)
    first = blocks[0]["corp_nm"]
    more = f" 외 {len(blocks) - 1}곳" if len(blocks) > 1 else ""
    subject = f"[조달핏] 이번 주 검토할 공고 — {first}{more} · {n_rows}건"
    E = html.escape
    date_label = f"{today.year}.{today.month:02d}.{today.day:02d} {DOW[today.weekday()]}"
    cta = f"{SITE}/recommendations?company={blocks[0]['bizrno_norm']}&{UTM}" if len(blocks) == 1 else f"{SITE}/saved?{UTM}"
    cta_label = "이 회사 추천 전체 보기 →" if len(blocks) == 1 else "검토함에서 전체 보기 →"

    h: list[str] = []
    t: list[str] = []
    preheader = E(blocks[0]["rows"][0].get("bid_ntce_nm") or "")
    h.append(f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{preheader}</div>')
    h.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C["paper"]};font-family:{FONT};color:{C["ink"]}"><tr><td align="center" style="padding:28px 16px 36px">')
    h.append('<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">')
    # 머리 — 로고 lockup · 날짜
    h.append('<tr><td style="padding:0 2px 14px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
             f'<td style="font-size:16px;font-weight:800;letter-spacing:-0.035em;line-height:22px"><img src="{SITE}/apple-icon" width="22" height="22" alt="" style="vertical-align:middle;border-radius:5px;margin-right:7px">'
             f'<a href="{SITE}/?{UTM}" style="color:{C["ink"]};text-decoration:none;vertical-align:middle">조달핏</a></td>'
             f'<td align="right" style="font-size:12px;color:{C["mute"]};white-space:nowrap">{date_label} · 주간 메일</td></tr></table></td></tr>')
    # 판
    h.append(f'<tr><td style="background:{C["panel"]};border:1px solid {C["hair"]};border-radius:8px;padding:26px 26px 24px">')
    h.append(f'<div style="font-size:11px;letter-spacing:0.04em;color:{C["mute"]}">저장한 회사의 새 공고</div>')
    h.append(f'<div style="font-size:22px;font-weight:700;letter-spacing:-0.02em;line-height:1.3;margin-top:6px">이번 주 검토할 공고 <span style="font-variant-numeric:tabular-nums">{n_rows}</span><span style="font-size:15px;font-weight:500">건</span></div>')
    h.append(f'<div style="font-size:13px;color:{C["g"]};margin-top:6px">최근 7일 등록 · 각 회사의 등록업종·공급물품·수주 이력 기준 · 적합 순</div>')
    t.append(f"조달핏 · {date_label} · 이번 주 검토할 공고 {n_rows}건\n")
    for b in blocks:
        link = f"{SITE}/recommendations?company={b['bizrno_norm']}&{UTM}"
        h.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px"><tr>'
                 f'<td style="border-left:2px solid {C["orange"]};padding-left:10px;font-size:15px;font-weight:700;line-height:1.3">{E(b["corp_nm"])}'
                 f'<div style="font-size:12.5px;font-weight:500;color:{C["mute"]};margin-top:3px">새 공고 {len(b["rows"])}건 &nbsp;·&nbsp; '
                 f'<a href="{link}" style="color:{C["ink"]};text-decoration:none;border-bottom:1px solid {C["ink"]}">추천 전체 보기 →</a></div></td></tr></table>')
        t.append(f"\n■ {b['corp_nm']} — 새 공고 {len(b['rows'])}건  ({link})")
        h.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px">')
        for i, r in enumerate(b["rows"], 1):
            nl = f"{SITE}/notices/{r.get('bid_ntce_no')}?{UTM}"
            org = r.get("dmnd_instt_nm") or r.get("ntce_instt_nm") or "—"
            clse = r.get("bid_clse_date")
            days = (date.fromisoformat(clse[:10]) - today).days if clse else None
            dl = "—" if days is None else (f"D-{days}" if days >= 0 else "마감")
            hot = days is not None and 0 <= days <= 7
            md = f"{clse[5:7]}.{clse[8:10]}" if clse else ""
            h.append(
                f'<tr><td valign="top" style="padding:13px 0;border-bottom:1px solid {C["rule"]};width:22px;font-size:11px;color:{C["mute"]};font-variant-numeric:tabular-nums">{i:02d}</td>'
                f'<td valign="top" style="padding:13px 10px 13px 0;border-bottom:1px solid {C["rule"]}">'
                f'<a href="{nl}" style="color:{C["ink"]};font-size:15px;font-weight:600;line-height:1.45;text-decoration:none">{E(r.get("bid_ntce_nm") or "")}</a>'
                f'<div style="font-size:12.5px;color:{C["g"]};margin-top:3px">{E(org)} &nbsp;·&nbsp; <span style="white-space:nowrap">추정가 <span style="color:{C["ink"]};font-weight:500;font-variant-numeric:tabular-nums">{_won(r.get("presmpt_prce"))}</span></span></div></td>'
                f'<td valign="top" align="right" style="padding:13px 0;border-bottom:1px solid {C["rule"]};width:58px;white-space:nowrap;font-variant-numeric:tabular-nums">'
                f'<div style="font-size:16px;font-weight:700;letter-spacing:-0.02em;color:{C["oink"] if hot else C["ink"]}">{dl}</div><div style="font-size:11px;color:{C["g"]};margin-top:2px">{md}</div></td></tr>'
            )
            t.append(f"{i:02d}. {r.get('bid_ntce_nm')}\n    {org} · 마감 {dl} {md} · 추정가 {_won(r.get('presmpt_prce'))}\n    {nl}")
        h.append("</table>")
    h.append(f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:22px"><tr><td style="background:{C["ink"]};border-radius:6px"><a href="{cta}" style="display:inline-block;padding:11px 16px;color:#ffffff;font-size:13.5px;font-weight:600;text-decoration:none">{cta_label}</a></td></tr></table>')
    h.append("</td></tr>")
    # 바닥
    h.append(f'<tr><td style="padding:16px 2px 0;font-size:12px;line-height:1.7;color:{C["mute"]}">추천은 검토 순서이며 낙찰을 예측하지 않습니다. 나라장터 공공데이터 기반 · 매일 05:00 갱신<br>'
             f'<a href="{SITE}/saved?{UTM}" style="color:{C["mute"]}">저장한 회사 바꾸기</a>')
    if unsubscribe:
        h.append(f' &nbsp;·&nbsp; <a href="{unsubscribe}" style="color:{C["mute"]}">이 메일 그만 받기</a>')
    h.append(f' &nbsp;·&nbsp; © {today.year} 조달핏</td></tr>')
    h.append("</table></td></tr></table>")
    t.append(f"\n{cta_label} {cta}\n추천은 검토 순서이며 낙찰을 예측하지 않습니다. 저장한 회사 바꾸기: {SITE}/saved")
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
