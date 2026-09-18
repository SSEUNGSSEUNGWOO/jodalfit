"""비교표 — 오늘 스냅샷 vs 전주 같은 요일(지표), vs 직전 스냅샷(키워드 순위 상승·하락·신규·이탈)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAP_DIR = REPO_ROOT / "docs" / "marketing" / "snapshots"


def load_snapshot(day: date) -> dict | None:
    p = SNAP_DIR / f"{day.isoformat()}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_snapshot(day: date, snap: dict) -> Path:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    p = SNAP_DIR / f"{day.isoformat()}.json"
    p.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def latest_snapshot_before(day: date, max_back: int = 7) -> dict | None:
    for back in range(1, max_back + 1):
        s = load_snapshot(day - timedelta(days=back))
        if s:
            return s
    return None


def dig(d: dict | None, path: str):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def row(label: str, cur: dict, prev: dict | None, path: str, fmt: str = "{:,}") -> tuple[str, str, str, str]:
    """(라벨, 오늘, 전주, 변화) — 값 없으면 '—'."""
    a, b = dig(cur, path), dig(prev, path)
    def f(v):
        return "—" if v is None else (fmt.format(v) if isinstance(v, (int, float)) else str(v))
    delta = "—"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        diff = a - b
        pct = f" ({diff / b * 100:+.0f}%)" if b else ""
        delta = f"{diff:+,.0f}{pct}" if float(diff).is_integer() else f"{diff:+.1f}{pct}"
    return label, f(a), f(b), delta


def keyword_moves(cur: dict[str, dict | None], prev: dict[str, dict | None] | None) -> dict[str, list]:
    """구글 평균 순위 기준. position 이 작을수록 상위. prev 없으면 전부 '신규' 대신 '기준 없음'."""
    out = {"up": [], "down": [], "new": [], "lost": [], "flat": [], "absent": []}
    for q, c in cur.items():
        p = (prev or {}).get(q) if prev else None
        cp = c["position"] if c else None
        pp = p["position"] if p else None
        if cp is None and pp is None:
            out["absent"].append(q)
        elif cp is None:
            out["lost"].append((q, pp))
        elif pp is None:
            out["new"].append((q, cp))
        elif cp < pp - 0.5:
            out["up"].append((q, pp, cp))
        elif cp > pp + 0.5:
            out["down"].append((q, pp, cp))
        else:
            out["flat"].append((q, cp))
    return out
