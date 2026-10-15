"""KURE-v1(1024d) 로컬 임베딩 — 요청 시점(Railway)·매일 배치(Actions)·GPU 백필 공용.

pooling 은 모델의 sentence-transformers 설정 그대로 **CLS**(`1_Pooling/config.json` 의
`pooling_mode_cls_token: true`) + L2 정규화(`2_Normalize`). mean pooling 아니다.

백엔드 두 개 — `KURE_BACKEND` 환경변수:
- `onnx`(기본) = int8 양자화 ONNX, onnxruntime CPU. 모델 파일은 GitHub Release 자산에서 첫 호출 때 받아 캐시.
  fp16 GPU 대비 코사인 평균 0.977 / top-100 후보 중복 0.868 — 근거·다른 양자화 변형은
  docs/recommender/exp-2026-10-15-embedding-model.md 부록.
- `torch` = sentence-transformers 원본(정확). 매일 배치·백필용. `uv sync --extra embed-cpu` 필요.
"""

from __future__ import annotations

import io
import os
import tempfile
import time
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_ID = "nlpai-lab/KURE-v1"
MODEL_URL = "https://github.com/SSEUNGSSEUNGWOO/jodalfit/releases/download/models-kure-v1-int8/kure-v1-int8-allops.zip"
DIM = 1024
MAX_LEN = 512
PAD_ID, PAD_TOKEN = 1, "<pad>"  # XLM-R 계열 — tokenizer.json 에 padding 설정이 없어 명시해야 한다


def _cache_dir() -> Path:
    from app.core.config import get_settings

    env = os.environ.get("KURE_MODEL_DIR") or get_settings().kure_model_dir
    return Path(env) if env else Path(tempfile.gettempdir()) / "kure-v1-int8"


def _backend() -> str:
    return os.environ.get("KURE_BACKEND", "onnx").lower()


def _download(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    print(f"KURE 모델 다운로드 {MODEL_URL} → {dest}")
    t0 = time.time()
    with urllib.request.urlopen(MODEL_URL) as r:  # noqa: S310 — 고정 상수 URL
        blob = r.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(dest)
    print(f"  {len(blob) / 1e6:.0f} MB, {time.time() - t0:.0f}s")


@lru_cache
def _onnx():
    import onnxruntime as ort
    from tokenizers import Tokenizer

    d = _cache_dir()
    if not (d / "model.onnx").exists():
        _download(d)
    tok = Tokenizer.from_file(str(d / "tokenizer.json"))
    tok.enable_truncation(MAX_LEN)
    tok.enable_padding(pad_id=PAD_ID, pad_token=PAD_TOKEN)
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = min(4, os.cpu_count() or 1)
    return tok, ort.InferenceSession(str(d / "model.onnx"), opts, providers=["CPUExecutionProvider"])


@lru_cache
def _torch():
    import torch
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(MODEL_ID, device="cuda" if torch.cuda.is_available() else "cpu")
    m.max_seq_length = MAX_LEN
    return m


def embed_texts_kure(texts: list[str], batch: int = 16) -> list[list[float]]:
    """CLS pooling + L2 정규화. 빈 텍스트는 placeholder 로 대체(OpenAI 쪽과 동일 관례)."""
    if not texts:
        return []
    cleaned = [t.strip() or "(empty)" for t in texts]

    if _backend() == "torch":
        # sentence-transformers 가 CLS pooling + Normalize 모듈을 그대로 적용한다.
        m = _torch()
        return m.encode(
            cleaned, batch_size=32, normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32).tolist()

    tok, sess = _onnx()
    out: list[list[float]] = []
    for i in range(0, len(cleaned), batch):
        enc = tok.encode_batch(cleaned[i : i + batch])
        h = sess.run(
            None,
            {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
            },
        )[0][:, 0]  # 출력 0 = token_embeddings → [:, 0] = CLS
        out.extend((h / np.linalg.norm(h, axis=1, keepdims=True)).astype(np.float32).tolist())
    return out


if __name__ == "__main__":
    sents = ["학교 급식 식자재 납품", "도로 포장 공사 감리 용역", "클라우드 서버 임차"]
    vecs = embed_texts_kure(sents)
    assert len(vecs) == 3, len(vecs)
    assert all(len(v) == DIM for v in vecs), [len(v) for v in vecs]
    norms = [float(np.linalg.norm(v)) for v in vecs]
    assert all(abs(n - 1.0) < 1e-3 for n in norms), norms
    t0 = time.perf_counter()
    embed_texts_kure(sents[:1])
    print(f"backend={_backend()} dim={DIM} norms={[round(n, 5) for n in norms]}")
    print(f"1문장 지연 {(time.perf_counter() - t0) * 1000:.0f} ms")
