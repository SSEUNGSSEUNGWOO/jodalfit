"""KURE-v1 → ONNX 양자화 export + fp16 GPU 대조. torch env 전용(1회 실행).

실행: C:\\dev\\ops\\jodalfit\\design\\.venv\\Scripts\\python.exe export_kure_onnx.py [out_dir] [variant]

variant (기본 mm-pc):
  all      전 op QInt8 (가장 작음 569MB, 코사인 0.977)
  mm       MatMul 만 per-tensor QInt8 (1.36GB, 0.977)
  mm-pc    MatMul 만 per-channel QInt8 (1.36GB, 0.985)  ← int8 중 최선
  ffn-pc   attention 제외 FFN MatMul 만 per-channel QInt8 (1.66GB, 0.991)
  fp32     양자화 없음 (2.27GB, 1.000)
산출: <out_dir>/ = model.onnx + tokenizer 파일 + POOLING.md
대조: 공고 텍스트 200건의 fp16 GPU 임베딩 vs ONNX 임베딩 코사인.
     합격 기준 평균 ≥ 0.995, 최소 ≥ 0.98 — **int8 어떤 변형도 평균 기준 미달**(2026-10-15 측정, 상세는
     docs/recommender/exp-2026-10-15-embedding-model.md).
pooling = CLS (KURE-v1 1_Pooling/config.json: pooling_mode_cls_token=true) + L2 정규화.
"""

import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서 한글/em-dash 출력 깨짐 방지

MODEL = "nlpai-lab/KURE-v1"
TEXTS_JSON = Path(r"C:\Users\USER\.claude\jobs\b5e41ab1\tmp\emb\texts-2026-08-01.json")
N_COMPARE = 200
MAX_LEN = 512
PAD_ID, PAD_TOKEN = 1, "<pad>"  # XLM-R 계열 — tokenizer.json 에 padding 설정이 없어 명시해야 한다

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "kure-v1-int8").resolve()
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "mm-pc"
FP32 = OUT.parent / "_kure-onnx-fp32"


def export_fp32() -> Path:
    from optimum.exporters.onnx import main_export

    if (FP32 / "model.onnx").exists():
        print(f"fp32 ONNX 이미 있음: {FP32}")
        return FP32
    print(f"export fp32 → {FP32}")
    # sentence-transformers 전체 그래프로 나온다: 출력 0 = token_embeddings, 1 = sentence_embedding(CLS+L2)
    main_export(MODEL, output=FP32, task="feature-extraction", opset=17)
    return FP32


def quantize(src: Path) -> None:
    import onnx
    from onnxruntime.quantization import QuantType, quantize_dynamic

    OUT.mkdir(parents=True, exist_ok=True)
    kw: dict = {"weight_type": QuantType.QInt8, "extra_options": {"MatMulConstBOnly": True}}
    if VARIANT != "all":
        kw["op_types_to_quantize"] = ["MatMul"]
        kw["per_channel"] = VARIANT.endswith("-pc")
    if VARIANT == "ffn-pc":
        g = onnx.load(src / "model.onnx", load_external_data=False).graph
        kw["nodes_to_exclude"] = [n.name for n in g.node if n.op_type == "MatMul" and "attention" in n.name.lower()]
    # quant_pre_process 는 external data(2.2GB) 를 임시 폴더로 못 옮겨 깨진다 — 생략(shape 추론 최적화 단계).
    if VARIANT == "fp32":
        shutil.copy2(src / "model.onnx", OUT / "model.onnx")
        shutil.copy2(src / "model.onnx_data", OUT / "model.onnx_data")
    else:
        print(f"quantize_dynamic variant={VARIANT}")
        quantize_dynamic(src / "model.onnx", OUT / "model.onnx", **kw)
    for name in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "config.json"):
        p = src / name
        if p.exists():
            shutil.copy2(p, OUT / name)
    (OUT / "POOLING.md").write_text(
        "# KURE-v1 ONNX\n\n"
        "- pooling: **CLS** (`token_embeddings[:, 0]`) — sentence-transformers `1_Pooling/config.json` 의 "
        "`pooling_mode_cls_token: true`. mean pooling 아님.\n"
        "- 그 뒤 L2 정규화 (`2_Normalize` 모듈). 그래프의 `sentence_embedding` 출력이 이미 CLS+L2 이지만, "
        "호출부에서 명시적으로 CLS + 정규화한다.\n"
        "- dim 1024, max_len 512 (운영 설정; 모델 자체는 8192 지원).\n"
        f"- padding: pad_id={PAD_ID} (`{PAD_TOKEN}`) — tokenizer.json 에 padding 설정이 없다.\n"
        f"- 양자화 variant: {VARIANT} (onnxruntime quantize_dynamic, weights only)\n"
        f"- 원본: {MODEL}\n",
        encoding="utf-8",
    )
    print(f"model.onnx: {(OUT / 'model.onnx').stat().st_size / 1e6:.0f} MB")


def embed_onnx(texts: list[str]) -> np.ndarray:
    import onnxruntime as ort
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(OUT / "tokenizer.json"))
    tok.enable_truncation(MAX_LEN)
    tok.enable_padding(pad_id=PAD_ID, pad_token=PAD_TOKEN)
    sess = ort.InferenceSession(str(OUT / "model.onnx"), providers=["CPUExecutionProvider"])
    out = []
    for i in range(0, len(texts), 16):
        enc = tok.encode_batch(texts[i : i + 16])
        h = sess.run(
            None,
            {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
            },
        )[0][:, 0]  # CLS
        out.append(h / np.linalg.norm(h, axis=1, keepdims=True))
    return np.vstack(out).astype(np.float32)


def embed_gpu(texts: list[str]) -> np.ndarray:
    import torch
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(MODEL, device="cuda" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        m.half()
    m.max_seq_length = MAX_LEN
    return m.encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)


def main() -> int:
    src = export_fp32()
    if not (OUT / "model.onnx").exists():
        quantize(src)

    texts = list(json.loads(TEXTS_JSON.read_text(encoding="utf-8"))["notices"].values())[:N_COMPARE]
    print(f"대조 {len(texts)}건")
    t0 = time.time()
    A = embed_onnx(texts)
    print(f"  ONNX CPU {time.time() - t0:.0f}s")
    B = embed_gpu(texts)
    assert A.shape == B.shape == (len(texts), 1024), (A.shape, B.shape)
    cos = (A * B).sum(axis=1)
    print(f"cosine mean {cos.mean():.5f} min {cos.min():.5f} p5 {np.percentile(cos, 5):.5f}")
    if cos.mean() < 0.995 or cos.min() < 0.98:
        print("FAIL: 기준(평균 >= 0.995, 최소 >= 0.98) 미달 - 진행 금지")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
