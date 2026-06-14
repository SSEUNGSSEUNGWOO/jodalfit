"""임베딩 공간 시각화 좌표 계산 — anchor 기반.

10개 도메인 anchor를 원형 시계 배치(IT=12시 시계방향)로 고정해두고,
회사·추천 결과 임베딩을 anchor 임베딩과의 유사도 가중 centroid로 2D 좌표 변환.

frontend의 `DOMAIN_KEYWORDS`와 의미 일관성을 맞추기 위해 키워드 셋 동기화 (단순화 — 동기화 부담은 PoC 단계에서 감내).
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from app.services.openai_client import embed_texts

# 시계 방향 배치 (IT 12시 = -90°, 시계방향 36°씩)
DOMAIN_ORDER = [
    "it",
    "ai",
    "content",
    "design",
    "event",
    "hrd",
    "education",
    "consulting",
    "medical",
    "construction",
]

DOMAIN_LABELS = {
    "it": "IT·시스템",
    "ai": "AI·데이터",
    "content": "콘텐츠",
    "design": "디자인",
    "event": "행사",
    "hrd": "HRD·연수",
    "education": "교육",
    "consulting": "컨설팅",
    "medical": "의료",
    "construction": "건설",
}

# 임베딩 입력 텍스트 (frontend DOMAIN_KEYWORDS와 동일 의미)
DOMAIN_TEXTS = {
    "it": "정보시스템 소프트웨어 SW 패키지 데이터베이스 서버 클라우드 ERP 인프라 웹 앱 유지보수 구축 솔루션 정보화",
    "ai": "인공지능 AI 머신러닝 딥러닝 빅데이터 DX AX 챗봇 생성형 분석모델",
    "content": "디지털콘텐츠 영상 비디오 미디어 게임 방송 애니메이션 이러닝 VR AR XR 실감 미디어아트",
    "design": "디자인 UI UX 그래픽 시각 환경디자인 산업디자인",
    "event": "행사 이벤트 대행 운영대행 박람회 페스티벌 축제 회의기획 기념 전시",
    "hrd": "위탁교육 위탁운영 직무교육 리더십 신입 승진 인재개발 연수 워크숍 역량강화 공통역량 양성",
    "education": "교육 학술 연구 학습 평생교육 강의 학교 대학 원격 교과 교원 수업 온라인교육",
    "consulting": "컨설팅 진단 자문 감리 전략 ISP 마스터플랜 조직진단 타당성 정책 평가",
    "medical": "의료 보건 의약품 진료 병원 약품 보건소 의료기기",
    "construction": "공사 건축 토목 신축 증축 도로 정비공사 리모델링 포장 교량",
}


@lru_cache(maxsize=1)
def _anchor_matrix() -> np.ndarray:
    """anchor 임베딩 10×1536 행렬. 프로세스 수명 동안 한 번만 계산."""
    texts = [DOMAIN_TEXTS[d] for d in DOMAIN_ORDER]
    embs = embed_texts(texts)
    return np.array(embs, dtype=np.float32)


def anchor_positions() -> list[dict]:
    """SVG 단위 원(-1~1) 위 anchor 좌표 + 라벨. 12시 시작 시계방향."""
    n = len(DOMAIN_ORDER)
    out: list[dict] = []
    for i, key in enumerate(DOMAIN_ORDER):
        angle = -math.pi / 2 + (2 * math.pi * i / n)  # 12시 시작
        out.append(
            {
                "key": key,
                "label": DOMAIN_LABELS[key],
                "x": math.cos(angle),
                "y": math.sin(angle),
            }
        )
    return out


def project_point(
    embedding: list[float] | np.ndarray,
    *,
    softmax_temperature: float = 8.0,
) -> tuple[float, float]:
    """주어진 임베딩을 anchor 좌표 평균(softmax 가중)으로 2D 투영.

    cosine similarity → softmax(τ=8) → anchor 좌표의 가중 평균.
    온도가 높을수록 가장 가까운 anchor 쪽으로 몰림(직관 정합).
    """
    A = _anchor_matrix()  # 10 × 1536
    v = np.asarray(embedding, dtype=np.float32)
    sims = A @ v  # 10, (둘 다 unit vector라 dot = cosine)
    weights = np.exp(softmax_temperature * (sims - sims.max()))
    weights = weights / weights.sum()
    positions = anchor_positions()
    x = float(sum(weights[i] * positions[i]["x"] for i in range(len(positions))))
    y = float(sum(weights[i] * positions[i]["y"] for i in range(len(positions))))
    return x, y


def project_many(embeddings: list[list[float]]) -> list[tuple[float, float]]:
    """배치 투영."""
    A = _anchor_matrix()
    V = np.asarray(embeddings, dtype=np.float32)  # N × 1536
    sims = V @ A.T  # N × 10
    sims = sims - sims.max(axis=1, keepdims=True)
    weights = np.exp(8.0 * sims)
    weights = weights / weights.sum(axis=1, keepdims=True)
    positions = anchor_positions()
    px = np.array([p["x"] for p in positions], dtype=np.float32)
    py = np.array([p["y"] for p in positions], dtype=np.float32)
    xs = weights @ px
    ys = weights @ py
    return list(zip(xs.tolist(), ys.tolist()))
