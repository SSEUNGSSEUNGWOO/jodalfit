"""입구 화면 재설계 — "너무 허전하다"(2026-10-23 승우님).

현행(entry-simple)은 검색창 하나 + 오늘 공고 다섯 줄이 전부라 화면 아래 3분의 2가 빈다.
세 안을 한 페이지에 놓고 알약으로 전환한다 — 같은 실제 데이터, 같은 폭.

  A 현행        검색창 + 오늘 등록 목록. 비교 기준.
  B 골든타임    검색창 + 현황 한 줄 + 사전규격 덩어리. 차별점을 입구로 끌어올린다.
  C 머리 세움   위에 제품 한 줄(큰 글자) + B + 마감 임박 목록. 화면을 끝까지 채운다.

원칙(docs/design/README.md): 주황은 선이지 면이 아니다 · 공문 톤 · 낙찰 예측이 아니라 디스커버리.
"오늘 등록된 공고"는 쓰지 않는다 — 수집이 한 번 밀리면 9건이 된다(2026-10-23 실측). 대신 마감 임박.

사용: cd backend && PYTHONPATH=".;../docs/design/scripts" uv run --no-sync python \
        ../docs/design/scripts/gen_entry_v2.py ../docs/design/prototypes/entry-v2.html
검증: 같은 환경에서 gen_entry_v2.py --check ../docs/design/prototypes/entry-v2.html
"""
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from html import escape as esc
from pathlib import Path

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from jobs.evaluate_recommender import connect  # noqa: E402

FONT = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/'
        'pretendardvariable-dynamic-subset.min.css">')


# ---------------------------------------------------------------- 데이터 (전부 실측)
def fetch(conn) -> dict:
    one = lambda q: conn.execute(q).fetchone()[0]
    active = one("""select count(*) from bid_notices
                     where bid_clse_date between current_date and current_date + 90
                       and embedding_k is not null
                       and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > now())""")
    spec_open = one("select count(*) from pre_specs where opnin_rgst_clse_dt > now()")
    spec_soon = one("""select count(*) from pre_specs
                        where opnin_rgst_clse_dt between now() and now() + interval '2 day'""")
    companies = one("select count(*) from companies where embedding_k is not null and optout_at is null")
    # 의견 마감이 가장 임박한 사전규격 — 입구에서 '지금 할 수 있는 일'을 보여주는 줄
    specs = [dict(nm=r[0], instt=r[1], clse=r[2], amt=r[3]) for r in conn.execute(
        """select prdct_clsfc_no_nm, rl_dminstt_nm, opnin_rgst_clse_dt, asign_bdgt_amt
             from pre_specs where opnin_rgst_clse_dt > now() and prdct_clsfc_no_nm is not null
            order by opnin_rgst_clse_dt limit 5""")]
    # 마감 임박 공고 — '오늘 등록' 대신. 수집이 밀려도 값이 흔들리지 않는다.
    # 나라장터는 같은 사업을 차수·재공고로 여러 번 올린다 — 제목+기관+마감이 같으면 한 줄로 본다.
    # 운영 추천 경로의 지문 중복 제거(recommend.py)와 같은 생각. 안 하면 입구에 같은 줄이 두 번 찍힌다.
    soon = [dict(nm=r[0], instt=r[1], clse=r[2], amt=r[3]) for r in conn.execute(
        """select distinct on (bid_ntce_nm, instt, bid_clse_date)
                  bid_ntce_nm, instt, bid_clse_date, amt from (
             select bid_ntce_nm,
                    coalesce(dmnd_instt_nm, ntce_instt_nm) instt,
                    bid_clse_date,
                    coalesce(presmpt_prce, asign_bdgt_amt) amt
               from bid_notices
              where bid_clse_date between current_date and current_date + 7
                and embedding_k is not null and bid_ntce_nm is not null
                and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > now())
              order by bid_clse_date, bid_ntce_no desc
              limit 200) t
            order by bid_ntce_nm, instt, bid_clse_date""")][:5]
    # 오늘 등록된 공고. 수집이 한 번 밀리면 한 자리로 떨어지므로(2026-10-23: 9건) 그대로 쓰면
    # 입구가 무너진다 — 오늘 치가 얇으면 최근 등록으로 바꿔 단다. 라벨도 같이 바뀐다.
    today_n = one("select count(*) from bid_notices where bid_ntce_date = current_date")
    fresh_today = today_n >= 20
    rows = conn.execute(
        """select distinct on (bid_ntce_nm, instt) bid_ntce_nm, instt, bid_ntce_date, bid_clse_date, amt from (
             select bid_ntce_nm, coalesce(dmnd_instt_nm, ntce_instt_nm) instt,
                    bid_ntce_date, bid_clse_date, coalesce(presmpt_prce, asign_bdgt_amt) amt
               from bid_notices
              where bid_ntce_date >= current_date - (case when %s then 0 else 3 end)
                and bid_ntce_nm is not null and embedding_k is not null
                -- 갓 올라왔는데 이미 마감인 공고가 있다(재공고·정정). 거르지 않으면 'D--1' 이 찍힌다.
                and bid_clse_date >= current_date
                and (bid_qlfct_rgst_dt is null or bid_qlfct_rgst_dt > now())
              order by bid_ntce_date desc, bid_ntce_no desc limit 300) t
            order by bid_ntce_nm, instt""", (fresh_today,)).fetchall()
    fresh = [dict(nm=r[0], instt=r[1], posted=r[2], clse=r[3], amt=r[4]) for r in rows]
    fresh.sort(key=lambda r: (r["posted"] or date.min), reverse=True)
    return dict(active=active, spec_open=spec_open, spec_soon=spec_soon, companies=companies,
                specs=specs, soon=soon, fresh=fresh[:5], today_n=today_n, fresh_today=fresh_today)


# ---------------------------------------------------------------- 표현 도우미
def won(v) -> str:
    if not v:
        return "—"
    v = int(v)
    if v >= 100_000_000:
        return f"{v / 100_000_000:,.1f}억"
    return f"{v / 10_000:,.0f}만"


KST = ZoneInfo("Asia/Seoul")


def dwhen(dt) -> str:
    """의견 마감 표시. 당일·익일이면 **시계 시각**을 준다 — 마감이 23시에 몰려 있어
    (2026-10-23 실측: 30일치 중 10,713건이 23시) '0시간 뒤' 같은 말은 10분 남은 것도 0으로 적는다.
    오늘 닫히는 건은 몇 시까지인지가 실제로 필요한 정보다."""
    if dt is None:
        return "—"
    now = datetime.now(timezone.utc)
    if dt <= now:
        return "마감"
    loc, today = dt.astimezone(KST), now.astimezone(KST).date()
    days = (loc.date() - today).days
    if days == 0:
        return f"오늘 {loc:%H:%M}"
    if days == 1:
        return f"내일 {loc:%H:%M}"
    return f"D-{days}"


def dleft(d) -> int | None:
    return None if d is None else (d - date.today()).days


# 리뉴얼 금지어 — frontend/scripts/check_results.py 와 같은 목록.
# "하세요"·"주십시오"가 막혀 있어 "입력해 주세요"는 쓸 수 없고, "넣으면"도 막혀 있다.
BANNED = ["낼 수 있", "왜 남았", "맞아요", "검토 인장", "하는 일", "넣으면", "안 맞아요",
          "이메일 구독", "매직링크", "회사 연결", "해드려요", "예요", "에요", "하세요", "주십시오"]

# ---------------------------------------------------------------- CSS
CSS = r"""
*{box-sizing:border-box} html,body{margin:0}
body{background:#faf9f7;color:#141414;font:400 14px/1.6 Pretendard,system-ui,sans-serif;
 -webkit-font-smoothing:antialiased}
.num{font-variant-numeric:tabular-nums;letter-spacing:-.02em}
a{color:inherit}
.wrap{width:1120px;max-width:100%;margin:0 auto;padding:0 20px;min-height:100vh;display:flex;flex-direction:column}
nav{display:flex;align-items:center;justify-content:space-between;padding:22px 0 0}
nav .lg{display:flex;align-items:center;gap:8px;font-weight:700;font-size:16px}
nav .lg i{width:7px;height:7px;border-radius:50%;background:#f97316;display:block}
nav .mn{display:flex;gap:22px;font-size:13.5px;color:#55554f}
nav .mn b{color:#141414;font-weight:600}
nav .mn u{text-decoration:none;border-bottom:1px solid #141414;padding-bottom:1px}

.v{display:none;flex:1;flex-direction:column} .v.on{display:flex}

/* 머리 — C 안에서만 */
.lede{margin:84px 0 0;font-size:34px;line-height:1.35;font-weight:650;letter-spacing:-.03em;max-width:760px}
.lede em{font-style:normal;border-bottom:2px solid #f97316;padding-bottom:2px}
.lede+.sub{margin-top:14px;color:#55554f;font-size:15px;max-width:640px}

/* 검색창 */
.box{margin:0 auto;width:100%;max-width:760px}
.box .f{display:flex;align-items:center;border:2px solid #f97316;background:#fff;border-radius:3px}
.box input{flex:1;border:0;outline:0;background:transparent;padding:19px 20px;font:inherit;font-size:19px}
.box input::placeholder{color:#9a9a95}
.box .go{padding:0 22px;font-weight:650;font-size:16px;border-left:1px solid #ece9e3;align-self:stretch;
 display:flex;align-items:center;cursor:pointer}
.box .go u{text-decoration:none;border-bottom:2px solid #141414}
.box .hint{margin-top:11px;color:#55554f;font-size:13.5px}
.box .hint b{font-weight:650;color:#141414}

/* 현황 한 줄 */
.stat{display:flex;gap:34px;margin:0 auto;width:100%;max-width:760px;padding-top:22px}
.stat div{display:flex;flex-direction:column;gap:3px}
.stat b{font-size:24px;font-weight:650;letter-spacing:-.03em}
.stat span{font-size:12.5px;color:#55554f}
.stat .hot b{color:#f97316}

/* 골든타임 덩어리 */
.gold{margin:40px auto 0;width:100%;max-width:760px;border-top:1px solid #141414;padding-top:14px}
.gold .hd{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.gold .hd b{font-size:15px;font-weight:650}
.gold .hd .why{color:#55554f;font-size:12.5px}
.gold .hd .all{font-size:13px;color:#55554f;border-bottom:1px solid #d8d6d0;cursor:pointer}
.gold ul{list-style:none;margin:10px 0 0;padding:0}
.gold li{display:grid;grid-template-columns:1fr auto auto;gap:14px;align-items:baseline;
 padding:9px 0;border-bottom:1px solid #ececea}
.gold li .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gold li .o{color:#55554f;font-size:12.5px;margin-left:8px}
.gold li .d{font-weight:650;font-size:13px;min-width:88px;text-align:right}
.gold li .d.hot{color:#f97316}
.gold li .a{color:#55554f;font-size:13px;min-width:62px;text-align:right}

/* 목록(현행 A / 마감 임박 C) */
.list{margin:40px auto 0;width:100%;max-width:760px}
.list .k{font-size:12.5px;color:#55554f;letter-spacing:.02em}
.list ul{list-style:none;margin:8px 0 0;padding:0}
.list li{display:grid;grid-template-columns:1fr auto auto;gap:14px;align-items:baseline;
 padding:9px 0;border-bottom:1px solid #ececea}
.list li .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list li .o{color:#55554f;font-size:12.5px;margin-left:8px}
.list li .d{font-size:13px;color:#55554f;min-width:76px;text-align:right}
.list li .d b{color:#141414;font-weight:650}
.list li .d b.hot{color:#f97316}
.list li .a{font-size:13px;color:#55554f;min-width:62px;text-align:right}
.list .more{margin-top:12px;font-size:13px;color:#55554f;border-bottom:1px solid #d8d6d0;
 display:inline-block;cursor:pointer}

.mid{flex:1;display:flex;flex-direction:column;justify-content:center;padding:0 0 40px}
.midA{flex:1;display:flex;flex-direction:column;justify-content:center;padding:0 0 40px}
foot{display:block;border-top:1px solid #ececea;margin-top:48px;padding:16px 0 28px;
 color:#8a8a85;font-size:12.5px;display:flex;justify-content:space-between;gap:16px}

/* 판 — 결과·회사 페이지와 같은 문법(종이 바닥 위 흰 판). 입구에서는 검색창 아래 내용을 담는다. */
.pane{background:#fff;border:1px solid #ececea;border-radius:6px;padding:22px 24px;
 margin:26px auto 0;width:100%;max-width:760px}
.pane .stat{padding-top:0;margin:0;max-width:none}
.pane .gold{margin:22px 0 0;max-width:none}
/* 묻는 줄 — 검색창의 머리다. 15px 로는 안내문처럼 읽혀 아무것도 묻지 않는 것 같았다. */
.ask{margin:0 auto 18px;width:100%;max-width:760px;font-size:26px;line-height:1.35;
 font-weight:650;letter-spacing:-.03em;color:#141414}
.ask b{font-weight:650;border-bottom:2px solid #f97316;padding-bottom:2px}

.ctl{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);display:flex;gap:2px;background:#fff;
 border:1px solid #e6e4df;border-radius:999px;padding:3px;font-size:12.5px;z-index:9;white-space:nowrap;
 box-shadow:0 2px 10px rgba(20,20,20,.06)}
.ctl span{padding:6px 14px;border-radius:999px;color:#55554f;cursor:pointer}
.ctl span.on{background:#141414;color:#fff}

@media (max-width:860px){
 .wrap{padding:0 16px}
 .ask{font-size:20px}
 .lede{font-size:25px;margin-top:48px}
 .box input{font-size:17px;padding:16px}
 .stat{gap:22px;flex-wrap:wrap}
 .gold li,.list li{grid-template-columns:1fr auto;row-gap:2px}
 .gold li .a,.list li .a{display:none}
 nav .mn{gap:14px}
}
"""


# ---------------------------------------------------------------- 조각
def nav_html() -> str:
    return ('<nav><span class="lg"><i></i>조달핏</span>'
            '<span class="mn"><b>추천</b><span>검토함</span><span>개선 기록</span><u>로그인</u></span></nav>')


def box_html(hint: str) -> str:
    return ('<div class="box"><div class="f">'
            '<input placeholder="회사명 · 사업자등록번호 · 업종 또는 품목" aria-label="회사 검색">'
            '<span class="go"><u>찾기</u></span></div>'
            f'<div class="hint">{hint}</div></div>')


def stat_html(d: dict) -> str:
    return ('<div class="stat">'
            f'<div><b class="num">{d["active"]:,}</b><span>지금 입찰 가능한 공고</span></div>'
            f'<div class="hot"><b class="num">{d["spec_open"]:,}</b><span>의견 접수 중인 사전규격</span></div>'
            f'<div><b class="num">{d["companies"]:,}</b><span>등록된 회사</span></div>'
            '</div>')


def gold_html(d: dict) -> str:
    li = "".join(
        f'<li><span class="t">{esc(s["nm"])}<span class="o">{esc(s["instt"] or "—")}</span></span>'
        f'<span class="d {"hot" if (s["clse"] - datetime.now(timezone.utc)).total_seconds() < 48 * 3600 else ""}">'
        f'{dwhen(s["clse"])}</span>'
        f'<span class="a num">{won(s["amt"])}</span></li>' for s in d["specs"])
    return ('<div class="gold"><div class="hd">'
            '<b>지금 의견 접수 중인 사전규격</b>'
            f'<span class="why">본공고가 뜨면 사양은 거의 못 바꿉니다 · {d["spec_soon"]:,}건은 이틀 안에 닫힙니다</span>'
            '</div>'
            f'<ul>{li}</ul></div>')


def list_html(d: dict, kind: str) -> str:
    """kind=today 는 현행 A 의 '오늘 등록'(수집이 밀리면 값이 무너진다), soon 은 마감 임박."""
    rows = d["soon"]
    if kind == "today":
        k = f"오늘 등록된 공고 {len(rows)}건"
    else:
        k = "이번 주 마감"
    li = "".join(
        f'<li><span class="t">{esc(r["nm"])}<span class="o">{esc(r["instt"] or "—")}</span></span>'
        f'<span class="d">마감 <b class="{"hot" if (dleft(r["clse"]) or 9) <= 3 else ""}">'
        f'D-{dleft(r["clse"])}</b></span>'
        f'<span class="a num">{won(r["amt"])}</span></li>' for r in rows)
    return f'<div class="list"><span class="k">{k}</span><ul>{li}</ul><span class="more">전체 보기 →</span></div>'


def fresh_html(d: dict) -> str:
    """오늘(또는 최근) 등록된 공고. 라벨이 실제 상태를 따라간다 — 숫자를 꾸미지 않는다."""
    if not d["fresh"]:
        return ""
    k = f'오늘 등록된 공고 {d["today_n"]:,}건' if d["fresh_today"] else "최근 등록된 공고"
    li = "".join(
        f'<li><span class="t">{esc(r["nm"])}<span class="o">{esc(r["instt"] or "—")}</span></span>'
        f'<span class="d">마감 <b class="{"hot" if (dleft(r["clse"]) or 9) <= 3 else ""}">'
        f'D-{dleft(r["clse"])}</b></span>'
        f'<span class="a num">{won(r["amt"])}</span></li>' for r in d["fresh"])
    return f'<div class="list"><span class="k">{k}</span><ul>{li}</ul><span class="more">전체 보기 →</span></div>'


def foot_html() -> str:
    return ('<foot><span>나라장터(국가종합전자조달) 공공데이터 기반 · 매일 05:00 갱신</span>'
            '<span>추천은 검토 순서이며 낙찰을 예측하지 않습니다.</span></foot>')


# ---------------------------------------------------------------- 안 셋
def variant_a(d: dict) -> str:
    hint = f'입찰 가능 공고 <b class="num">{d["active"]:,}</b>건 중 참가 자격을 확인해 선별합니다'
    return f'<div class="v" data-v="a"><div class="midA">{box_html(hint)}{list_html(d, "today")}</div>{foot_html()}</div>'


def variant_b(d: dict) -> str:
    hint = "회사를 고르면 등록업종·공급물품·수주 이력으로 맞는 공고만 남깁니다"
    return (f'<div class="v" data-v="b"><div class="mid">{box_html(hint)}{stat_html(d)}{gold_html(d)}</div>'
            f'{foot_html()}</div>')


def variant_d(d: dict) -> str:
    """B 에 판을 씌우고 검색창 위에 가벼운 한 줄. 2026-10-23 승우님 요청.
    "입력해 주세요"는 쓸 수 없다 — 금지어 "하세요"에 걸린다. 공문 톤으로 묻는 형태를 쓴다."""
    ask = '<div class="ask">어느 <b>회사</b>의 공고를 찾습니까</div>'
    hint = "회사명 · 사업자등록번호 · 업종 또는 품목 중 아는 것 하나면 됩니다"
    return (f'<div class="v" data-v="d"><div class="mid">{ask}{box_html(hint)}'
            f'<div class="pane">{stat_html(d)}{gold_html(d)}</div>{fresh_html(d)}</div>{foot_html()}</div>')


def variant_c(d: dict) -> str:
    hint = "회사를 고르면 등록업종·공급물품·수주 이력으로 맞는 공고만 남깁니다"
    lede = ('<p class="lede">남들이 입찰공고를 볼 때, <em>사전규격부터</em> 봅니다.</p>'
            '<p class="sub">사양에 의견을 내는 기간은 3~10일입니다. 본공고가 뜨면 거의 못 바꿉니다.</p>')
    return (f'<div class="v" data-v="c">{lede}<div style="margin-top:34px">{box_html(hint)}{stat_html(d)}'
            f'{gold_html(d)}{list_html(d, "soon")}</div>{foot_html()}</div>')


JS = r"""
const vs = [...document.querySelectorAll('.v')], ps = [...document.querySelectorAll('.ctl span')];
function pick(k){ vs.forEach(v => v.classList.toggle('on', v.dataset.v === k));
  ps.forEach(p => p.classList.toggle('on', p.dataset.v === k)); }
ps.forEach(p => p.addEventListener('click', () => pick(p.dataset.v)));
pick('d');
"""


def build(d: dict) -> str:
    ctl = ('<div class="ctl">'
           '<span data-v="a">A 현행</span><span data-v="b">B 골든타임</span>'
           '<span data-v="c">C 머리 세움</span><span data-v="d">D 판 + 묻는 줄</span>'
           '</div>')
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>입구 화면 재설계 — A 현행 / B 골든타임 / C 머리 세움</title>{FONT}'
            f'<style>{CSS}</style></head><body><div class="wrap">{nav_html()}'
            f'{variant_a(d)}{variant_b(d)}{variant_c(d)}{variant_d(d)}</div>{ctl}<script>{JS}</script></body></html>')


def check(path: str) -> None:
    from playwright.sync_api import sync_playwright
    out = Path(path).resolve().parent
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        pg.goto(Path(path).resolve().as_uri())
        for k in ("a", "b", "c", "d"):
            pg.click(f'.ctl [data-v="{k}"]')
            pg.wait_for_timeout(150)
            s = pg.evaluate("""() => { const v = document.querySelector('.v.on'); const cs = e => getComputedStyle(e);
              const all = [...v.querySelectorAll('*')];
              return { h: document.documentElement.scrollHeight, box: !!v.querySelector('.box input'),
                rows: v.querySelectorAll('li').length,
                orangeFaces: all.filter(e => cs(e).backgroundColor === 'rgb(249, 115, 22)').length,
                over: document.documentElement.scrollWidth > window.innerWidth } }""")
            assert s["box"], (k, "검색창이 없다")
            assert not s["over"], (k, "가로 넘침")
            # 주황은 선이지 면이 아니다 — 로고 점 하나만 면으로 허용한다(docs/design/README.md)
            assert s["orangeFaces"] <= 1, (k, s)
            txt = pg.evaluate("document.body.innerText")
            bad = [w for w in BANNED if w in txt]
            assert not bad, (k, bad)
            # 마감이 지난 공고가 목록에 섞이면 'D--1' 로 찍힌다 — 재공고·정정 건이 그렇다.
            assert "D--" not in txt, (k, "마감 지난 공고가 목록에 있다")
            pg.screenshot(path=str(out / f"_shot_entry_v2_{k}.png"), full_page=True)
            print(f"  {k}: 높이 {s['h']}px · 줄 {s['rows']}개 · 주황 면 {s['orangeFaces']}")
        pg2 = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        pg2.goto(Path(path).resolve().as_uri())
        pg2.click('.ctl [data-v="c"]')
        pg2.wait_for_timeout(150)
        assert not pg2.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "390 가로 넘침"
        pg2.screenshot(path=str(out / "_shot_entry_v2_390.png"), full_page=True)
        b.close()
    print("ok entry-v2")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        check(sys.argv[2])
    else:
        conn = connect()
        d = fetch(conn)
        Path(sys.argv[1]).write_text(build(d), encoding="utf-8", newline="\n")
        print(f"written {sys.argv[1]}")
        print(f"  입찰가능 {d['active']:,} · 사전규격 {d['spec_open']:,}(이틀 내 {d['spec_soon']:,}) · 회사 {d['companies']:,}")
