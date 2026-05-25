"""Evaluator 에이전트 — Codex CLI.

rubric.yaml 기준 0~5점 평가 → 가중 점수 + feedback.
threshold 미달 시 caller가 writer 재호출.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml


CODEX_TIMEOUT = 300


def load_rubric() -> dict:
    with open(Path(__file__).parent / "rubric.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _codex_call(prompt: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    codex_cmd = shutil.which("codex") or "codex"
    result = subprocess.run(
        [codex_cmd, "exec", "--skip-git-repo-check", "-s", "read-only", "-"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=CODEX_TIMEOUT,
        env=env,
        encoding="utf-8",
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"codex CLI 실패: {result.stderr[:300]}")
    return result.stdout


def _extract_json(s: str) -> dict:
    start = s.find("{")
    end = s.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError(f"JSON 추출 실패: {s[:200]}")
    return json.loads(s[start:end])


def evaluate(draft_markdown: str, content_type: str) -> dict:
    """draft 마크다운 본문 평가. content_type: 'picks' | 'market'."""
    rubric = load_rubric()
    criteria_text = "\n".join(
        f"- **{c['name']}** (가중치 {c['weight']}, 최대 {c['max_score']}점): {c['description']}"
        for c in rubric["criteria"]
    )

    prompt = f"""다음 한국 공공조달 주간 인사이트 마크다운을 아래 루브릭으로 평가하세요.

콘텐츠 타입: {content_type}
- picks: 영업/대표용 큐레이션 (TOP 10 공고 + 공고당 한 줄 blurb)
- market: 시장 관찰자용 데이터 리포트 (표 + 한 단락 narrative)

평가는 LLM이 생성한 부분(picks의 blurb, market의 narrative)에 집중하세요.
표/수치는 시스템이 직접 DB에서 가져온 것이라 사실 정확. 다만 narrative가 표 수치와
어긋나거나 표에 없는 숫자를 만들어내면 factual_accuracy 감점.

## 루브릭
{criteria_text}

## 통과 기준
- 가중 점수 {rubric['pass_threshold']} 이상
- 위 5개 기준 모두 3점 이상

## 응답 형식 (JSON만 출력, 마크다운 코드펜스 금지)
{{
  "scores": {{
    "factual_accuracy": 0~5,
    "concrete": 0~5,
    "tone": 0~5,
    "relevance": 0~5,
    "format": 0~5
  }},
  "weighted_score": 0~5,
  "pass": true/false,
  "feedback": "구체적인 개선 요청. 감점 문장이 있으면 그 문장을 인용. 어떤 표현을 어떤 표현으로 바꿔야 하는지 명시.",
  "strengths": "잘 된 부분 1~2줄"
}}

## 평가 대상 마크다운
{draft_markdown}
"""
    raw = _codex_call(prompt)
    result = _extract_json(raw)

    # 가중 점수 재계산 (safety)
    scores = result.get("scores", {})
    weighted = sum(
        scores.get(c["name"], 0) * c["weight"] for c in rubric["criteria"]
    )
    result["weighted_score"] = round(weighted, 2)
    min_score = min(scores.values()) if scores else 0
    result["pass"] = (
        weighted >= rubric["pass_threshold"] and min_score >= 3
    )
    result["pass_threshold"] = rubric["pass_threshold"]
    result["max_retries"] = rubric.get("max_retries", 2)
    return result
