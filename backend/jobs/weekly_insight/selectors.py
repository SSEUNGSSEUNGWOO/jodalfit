"""Picks 큐레이션 + Market 통계 (LLM 없음, 순수 룰)."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date


# 도메인 사전 — `frontend/src/lib/company-profile.ts`의 DOMAIN_KEYWORDS·DOMAIN_LABELS 미러.
# 프론트에서 회사 활동 영역 분석에 쓰는 것과 같은 사전이라 카테고리 정의 일관성 확보.
# 수정 시 양쪽 함께 갱신 필요.
DOMAIN_LABELS: dict[str, str] = {
    "it": "IT·시스템",
    "content": "콘텐츠 개발",
    "education": "교육·학술",
    "hrd": "HRD·연수",
    "consulting": "컨설팅",
    "ai": "AI·데이터",
    "design": "디자인",
    "event": "행사·대행",
    "construction": "건설",
    "medical": "의료·보건",
}

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "it": [
        # NOTE: "유지관리" 제거 — 청소·시설 관리용역까지 걸림. "유지보수"만 유지.
        "소프트웨어", "sw", "시스템", "정보시스템", "패키지", "데이터베이스",
        "컴퓨터", "네트워크", "서버", "클라우드", "erp", "인프라", "웹", "앱",
        "어플", "유지보수", "구축", "포털", "솔루션", "전산", "정보화",
    ],
    "content": [
        # NOTE: "영상" 제거 — CCTV·영상감시장치 등 건설 관급자재까지 걸림.
        "디지털콘텐츠", "콘텐츠", "비디오", "미디어", "게임", "방송",
        "애니메이션", "이러닝", "vr", "ar", "xr", "실감", "미디어아트",
    ],
    "education": [
        "교육", "학술", "연구", "학습", "평생교육", "강의", "학교", "대학",
        "원격", "교과", "학생", "교원", "교수", "수업", "온라인교육",
    ],
    "hrd": [
        "위탁교육", "위탁운영", "직무", "리더십", "신입", "승진", "승격",
        "인재", "인재개발", "연수", "워크숍", "역량강화", "공통역량", "양성",
        "직급", "실무",
    ],
    "consulting": [
        # NOTE: "감리" 제거 — 대부분 건설 감리. construction으로 재분류.
        "컨설팅", "진단", "자문", "전략", "isp", "마스터플랜",
        "조직진단", "타당성", "정책", "평가",
    ],
    "ai": [
        "ai", "인공지능", "ml", "머신러닝", "딥러닝", "데이터", "dx", "ax",
        "빅데이터", "챗봇", "분석모델", "생성형",
    ],
    "design": [
        "디자인", "ui", "ux", "그래픽", "시각", "환경디자인", "산업디자인",
    ],
    "event": [
        # NOTE: "대행" 제거 — "감독권한대행/관리대행" 등 건설·운영에 광범위. "운영대행"만 유지.
        "행사", "이벤트", "운영대행", "박람회", "페스티벌", "축제",
        "회의기획", "기념", "전시",
    ],
    "construction": [
        # NOTE: 건설 감리·대행 관련 추가 — 이전에 consulting/event로 오분류되던 케이스 흡수.
        "공사", "건축", "토목", "신축", "증축", "도로", "정비공사",
        "리모델링", "포장", "교량", "감리", "감독권한대행", "관리대행",
        "건설사업관리", "하수처리시설", "하수관로",
    ],
    "medical": [
        "의료", "보건", "의약품", "진료", "병원", "약품", "보건소", "의료기기",
    ],
}


_PRIVATE_TOKENS = ("주식회사", "(주)", "㈜", "유한회사", "유한책임회사", "합자회사", "합명회사")

_INSTT_BLACKLIST = {
    "각 수요기관",
    "수요기관",
    "수요처",
    "각수요기관",
    "각 기관",
}


def is_private_org(name: str | None) -> bool:
    if not name:
        return False
    return any(tok in name for tok in _PRIVATE_TOKENS)


def institution_ok(name: str | None) -> bool:
    if not name:
        return False
    if name.strip() in _INSTT_BLACKLIST:
        return False
    if is_private_org(name):
        return False
    return True


def name_key(nm: str | None) -> str:
    if not nm:
        return ""
    s = nm
    s = re.sub(r"\(재공고\)|\(긴급\)|\(공동\)|\(2차\)|\(3차\)|\(4차\)|\(5차\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:30]


def format_amount(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.1f}조"
    if v >= 100_000_000:
        return f"{v / 100_000_000:.1f}억"
    if v >= 10_000:
        return f"{v / 10_000:.0f}만"
    return f"{int(v):,}"


def days_until(date_str: str | None, ref: date) -> int | None:
    if not date_str:
        return None
    try:
        d = date.fromisoformat(date_str[:10])
    except Exception:
        return None
    return (d - ref).days


def pick_top10(notices: list[dict], today: date) -> list[dict]:
    candidates = []
    for n in notices:
        instt = n.get("dmnd_instt_nm") or n.get("ntce_instt_nm")
        if not institution_ok(instt):
            continue
        price = n.get("presmpt_prce") or n.get("asign_bdgt_amt") or 0
        if price and price < 100_000_000:
            continue
        d = days_until(n.get("bid_clse_date"), today)
        if d is None or d < 0:
            continue
        candidates.append(
            {**n, "_dday": d, "_price": price or 0, "_key": name_key(n.get("bid_ntce_nm"))}
        )

    def score(n):
        price_score = min(n["_price"] / 1_000_000_000, 5.0)
        d = n["_dday"]
        if d < 3:
            dday_score = 0.3
        elif d <= 14:
            dday_score = 1.0
        elif d <= 30:
            dday_score = 0.7
        else:
            dday_score = 0.4
        return price_score * dday_score

    candidates.sort(key=score, reverse=True)

    picked: list[dict] = []
    inst_count: Counter = Counter()
    bsns_count: Counter = Counter()
    seen_keys: set[str] = set()
    for c in candidates:
        if c["_key"] and c["_key"] in seen_keys:
            continue
        instt = c.get("dmnd_instt_nm") or c.get("ntce_instt_nm") or "—"
        bsns = c.get("bsns_div_nm") or "—"
        if inst_count[instt] >= 1:
            continue
        if bsns_count[bsns] >= 5:
            continue
        picked.append(c)
        if c["_key"]:
            seen_keys.add(c["_key"])
        inst_count[instt] += 1
        bsns_count[bsns] += 1
        if len(picked) >= 10:
            break
    return picked


def classify_notice(notice: dict) -> str | None:
    """공고를 도메인 하나로 분류. 매칭 도메인 없으면 None.

    입력 텍스트 = 공고명 + 업무구분. substring 매칭으로 각 도메인 hit 수 계산.
    최다 hit 도메인 선택 (tie 시 DOMAIN_KEYWORDS 순서상 앞).
    """
    text = " ".join(
        filter(None, [notice.get("bid_ntce_nm"), notice.get("bsns_div_nm")])
    ).lower()
    if not text:
        return None

    best_domain: str | None = None
    best_count = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        count = sum(text.count(kw.lower()) for kw in keywords)
        if count > best_count:
            best_count = count
            best_domain = domain
    return best_domain


def pick_top_by_category(
    notices: list[dict],
    today: date,
    per_cat: int = 5,
    min_cat: int = 5,
) -> dict[str, list[dict]]:
    """카테고리별로 분류한 뒤 각 카테고리 안에서 TOP `per_cat` 선별.

    `per_cat` = 카테고리당 최종 픽 수, `min_cat` = 발행 임계값(픽 수 < min_cat이면 스킵).
    반환은 domain → picks. 순서는 DOMAIN_LABELS 정의 순서.
    """
    # 1) 도메인별로 후보 집계 (필터링은 pick_top10과 동일 로직으로 아래에서 재사용)
    by_domain: dict[str, list[dict]] = {d: [] for d in DOMAIN_LABELS}
    for n in notices:
        domain = classify_notice(n)
        if domain is None:
            continue
        by_domain[domain].append(n)

    result: dict[str, list[dict]] = {}
    for domain, cat_notices in by_domain.items():
        picks = pick_top10(cat_notices, today)[:per_cat]
        if len(picks) >= min_cat:
            result[domain] = picks
    return result


MIN_PREV_FOR_WOW = 200


def market_stats(notices: list[dict], prev_notices: list[dict]) -> dict:
    total = len(notices)
    prev_total = len(prev_notices)
    wow_reliable = prev_total >= MIN_PREV_FOR_WOW
    wow = ((total - prev_total) / prev_total * 100) if (prev_total and wow_reliable) else None

    bsns_counter: Counter = Counter()
    instt_counter: Counter = Counter()
    prices: list[float] = []

    for n in notices:
        bsns = n.get("bsns_div_nm") or "기타"
        bsns_counter[bsns] += 1
        instt = n.get("dmnd_instt_nm") or n.get("ntce_instt_nm")
        if institution_ok(instt):
            instt_counter[instt] += 1
        p = n.get("presmpt_prce") or n.get("asign_bdgt_amt")
        if p:
            prices.append(float(p))

    buckets = {
        "1억 미만": 0,
        "1억~10억": 0,
        "10억~50억": 0,
        "50억~100억": 0,
        "100억 이상": 0,
    }
    for p in prices:
        if p < 100_000_000:
            buckets["1억 미만"] += 1
        elif p < 1_000_000_000:
            buckets["1억~10억"] += 1
        elif p < 5_000_000_000:
            buckets["10억~50억"] += 1
        elif p < 10_000_000_000:
            buckets["50억~100억"] += 1
        else:
            buckets["100억 이상"] += 1

    avg_price = sum(prices) / len(prices) if prices else 0
    median_price = sorted(prices)[len(prices) // 2] if prices else 0

    return {
        "total": total,
        "prev_total": prev_total,
        "wow_pct": wow,
        "wow_reliable": wow_reliable,
        "bsns_dist": bsns_counter.most_common(),
        "top_institutions": instt_counter.most_common(10),
        "price_buckets": buckets,
        "price_sample_count": len(prices),
        "avg_price": avg_price,
        "median_price": median_price,
    }
