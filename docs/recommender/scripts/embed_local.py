"""로컬 모델로 임베딩 → npz. 사용: python embed_local.py <model_key> <texts.json> <out.npz>
model_key: bge  (BAAI/bge-m3) | kure (nlpai-lab/KURE-v1)
"""
import json, sys, time
import numpy as np, torch
from sentence_transformers import SentenceTransformer

MODELS = {"bge": "BAAI/bge-m3", "kure": "nlpai-lab/KURE-v1"}
key, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(src, encoding="utf-8"))
keys = list(d["notices"].keys()); n_texts = [d["notices"][k] for k in keys]
i_texts = d["texts"]
dev = "cuda" if torch.cuda.is_available() else "cpu"
print(f"{key} on {dev}: {len(n_texts):,} notices + {len(i_texts)} industry texts")
t0 = time.time()
m = SentenceTransformer(MODELS[key], device=dev)
m.half() if dev == "cuda" else None
m.max_seq_length = 512
N = m.encode(n_texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
I = m.encode(i_texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False) if i_texts else np.zeros((0, N.shape[1]), dtype=np.float32)
np.savez_compressed(out, keys=np.array(keys), N=N.astype(np.float32), texts=np.array(i_texts, dtype=object), I=I.astype(np.float32))
print(f"done {key}: dim {N.shape[1]}, {time.time()-t0:.0f}s → {out}")
