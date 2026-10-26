"""키워드 모드 질의의 영문 약어 풀이 — 임베딩 전에 뜻을 붙인다.

"si" 두 글자는 임베딩 모델(KURE)에게 뜻이 거의 없어 글자꼴이 비슷한 공고(유한요소해석·하수관로)를 잡았다
(2026-10-26, 한 사람이 "si" 를 세 번 다시 침). 조달 현장에서 흔한 약어를 한글 풀이로 보강한다.

원문은 그대로 두고 뒤에 풀이를 덧붙인다 — 공고 제목에 "SI" 가 그대로 쓰이는 경우도 잡아야 한다.
회사 모드 점수에는 손대지 않는다(키워드 질의 문장만). 자체 점검: `uv run python -m app.recommender.keyword_expand`
"""

from __future__ import annotations

import re

# 약어(소문자) → 한글 풀이. 공고 제목·분류명에 실제로 쓰이는 말로 적는다.
ABBREVIATIONS: dict[str, str] = {
    "si": "시스템 통합 정보시스템 구축 소프트웨어 개발",
    "sm": "시스템 유지관리 운영 유지보수",
    "isp": "정보화 전략 계획 수립",
    "ismp": "정보시스템 마스터플랜 수립",
    "erp": "전사적 자원관리 시스템",
    "crm": "고객관리 시스템",
    "gis": "지리정보시스템 공간정보",
    "bim": "건축정보모델링 설계",
    "cctv": "영상감시 카메라 설치",
    "vms": "영상관리 시스템",
    "led": "조명 등기구",
    "ai": "인공지능",
    "iot": "사물인터넷 센서",
    "rpa": "업무 자동화 로봇 프로세스",
    "ocr": "문서 인식 광학문자판독",
    "db": "데이터베이스",
    "dbms": "데이터베이스 관리시스템",
    "ups": "무정전 전원장치",
    "hvac": "공조 냉난방 설비",
    "ev": "전기차 충전기 충전시설",
    "pc": "컴퓨터 데스크톱",
    "vr": "가상현실 콘텐츠",
    "ar": "증강현실 콘텐츠",
    "lms": "학습관리시스템 이러닝",
    "ems": "에너지관리시스템",
    "bms": "빌딩 자동제어 시스템",
    "ess": "에너지저장장치",
    "pv": "태양광 발전설비",
    "mro": "소모성 자재 구매",
    "pm": "사업관리",
    "pmo": "사업관리 조직 감리",
    "ict": "정보통신 기술",
    "it": "정보기술 정보시스템",
    "sw": "소프트웨어",
    "hw": "하드웨어 장비",
    "dx": "디지털 전환",
    "ux": "사용자 경험 화면 설계",
    "ui": "사용자 인터페이스 화면 설계",
    "api": "연계 인터페이스",
    "eai": "시스템 연계 통합",
    "pacs": "의료영상 저장전송 시스템",
    "emr": "전자의무기록 시스템",
    "kiosk": "키오스크 무인단말기",
    "lte": "무선통신 망",
    "5g": "5세대 이동통신 망",
    "nas": "네트워크 저장장치 스토리지",
    "san": "스토리지 네트워크",
    "was": "웹 애플리케이션 서버",
    "iptv": "인터넷 방송 영상 서비스",
}

# 영문·숫자 토큰 — 한글이 붙어 있어도("si업체") 잡는다. 앞뒤가 영문이면 단어 속 조각이라 제외("main" 의 ai).
_TOKEN = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z0-9]{0,5}(?![A-Za-z])")


def expand_keywords(text: str) -> str:
    """약어가 있으면 '원문 (풀이)' 로, 없으면 원문 그대로."""
    seen: list[str] = []
    for m in _TOKEN.finditer(text):
        key = m.group(0).lower()
        exp = ABBREVIATIONS.get(key)
        if exp and exp not in seen:
            seen.append(exp)
    if not seen:
        return text
    return f"{text} ({' / '.join(seen)})"


if __name__ == "__main__":
    cases = {
        "si": "si (시스템 통합 정보시스템 구축 소프트웨어 개발)",
        "SI 사업": "SI 사업 (시스템 통합 정보시스템 구축 소프트웨어 개발)",
        "si업체 sm": "si업체 sm (시스템 통합 정보시스템 구축 소프트웨어 개발 / 시스템 유지관리 운영 유지보수)",
        "main road": "main road",            # 단어 속 ai 는 약어가 아니다
        "하수처리시설 관리대행": "하수처리시설 관리대행",
        "cctv cctv": "cctv cctv (영상감시 카메라 설치)",   # 중복 한 번만
        "ERP 구축": "ERP 구축 (전사적 자원관리 시스템)",
    }
    for src, want in cases.items():
        got = expand_keywords(src)
        assert got == want, (src, got, want)
    print(f"keyword_expand: ok ({len(ABBREVIATIONS)} 약어, {len(cases)} 사례)")
