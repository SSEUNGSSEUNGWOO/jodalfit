"""여러 임베딩 모델로 texts.json → npz (2026-11-04 재대결, embed_local.py 의 확장).

사용: cd backend && uv run python ../docs/recommender/scripts/embed_models.py <model_key> <texts.json> <out.npz>
- 공고 텍스트(N)는 문서, 업종 텍스트(I)는 질의로 본다. 지시문이 필요한 모델(qwen3·e5·arctic)은 I 에만 질의 접두어를 붙인다
  — 회사 벡터는 I 와 이력 공고 N 의 가중합이라 N 은 전 모델 공통으로 접두어 없음.
- GPU fp16, max_seq 512, L2 정규화. openai-large 는 API(text-embedding-3-large, 3072d).
"""
import json, os, sys, time
import numpy as np

MODELS = {
    "kure": ("nlpai-lab/KURE-v1", None),
    "bge": ("BAAI/bge-m3", None),
    "qwen06": ("Qwen/Qwen3-Embedding-0.6B", "Instruct: Given a company's registered industries and supplied products, retrieve Korean public procurement bid notices the company could bid on\nQuery: "),
    "e5": ("intfloat/multilingual-e5-large-instruct", "Instruct: Given a company's registered industries and supplied products, retrieve Korean public procurement bid notices the company could bid on\nQuery: "),
    "arctic": ("Snowflake/snowflake-arctic-embed-l-v2.0", "query: "),
    "openai-large": ("text-embedding-3-large", None),
    "gemini": ("gemini-embedding-001", None),  # REST batchEmbedContents, 문서 RETRIEVAL_DOCUMENT / 질의 RETRIEVAL_QUERY, 3072d
    "gemini-1536": ("gemini-embedding-001", 1536),  # outputDimensionality(MRL) — pgvector HNSW 는 2000d 까지라 운영엔 이쪽이 필요
    "gemini-768": ("gemini-embedding-001", 768),
    "gemini-sym": ("gemini-embedding-001", "SEMANTIC_SIMILARITY"),  # 질의·문서 같은 taskType — 비대칭(RETRIEVAL_*)의 효과 확인용
}
key, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
name, qprefix = MODELS[key]
d = json.load(open(src, encoding="utf-8"))
keys = list(d["notices"].keys()); n_texts = [d["notices"][k] for k in keys]; i_texts = d["texts"]
print(f"{key} ({name}): {len(n_texts):,} notices + {len(i_texts)} industry texts", flush=True)
t0 = time.time()

if key == "openai-large":
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../../backend/.env"))
    client = OpenAI()

    def embed(texts: list[str]) -> np.ndarray:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), 256):
            batch = [t[:6000] for t in texts[i:i + 256]]
            for attempt in range(5):
                try:
                    r = client.embeddings.create(model=name, input=batch); break
                except Exception as e:  # 429·일시 오류
                    if attempt == 4: raise
                    print(f"  retry {attempt + 1}: {e}", flush=True); time.sleep(5 * (attempt + 1))
            vecs.extend(x.embedding for x in r.data)
            if (i // 256) % 20 == 0: print(f"  {i + len(batch):,}/{len(texts):,}", flush=True)
        X = np.array(vecs, dtype=np.float32)
        return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    N = embed(n_texts); I = embed(i_texts) if i_texts else np.zeros((0, N.shape[1]), dtype=np.float32)
elif key.startswith("gemini"):
    import httpx
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../../backend/.env"))
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{name}:batchEmbedContents"
    out_dim = qprefix if isinstance(qprefix, int) else None
    sym_task = qprefix if isinstance(qprefix, str) else None

    def embed(texts: list[str], task: str) -> np.ndarray:
        task = sym_task or task
        vecs: list[list[float]] = []
        with httpx.Client(timeout=120) as c:
            for i in range(0, len(texts), 100):
                batch = texts[i:i + 100]
                body = {"requests": [{"model": f"models/{name}", "content": {"parts": [{"text": t[:6000]}]}, "taskType": task,
                                      **({"outputDimensionality": out_dim} if out_dim else {})} for t in batch]}
                for attempt in range(15):  # 분당 한도(RPM·TPM)라 한 번에 하나만 돌리고 길게 기다린다 — 7개 병렬은 3분 만에 포기했다(2026-11-05)
                    try:
                        r = c.post(url, params={"key": api_key}, json=body)
                    except httpx.HTTPError as e:
                        print(f"  net retry {attempt + 1}: {e}", flush=True); time.sleep(15); continue
                    if r.status_code == 200: break
                    print(f"  {r.status_code} retry {attempt + 1}: {r.text[:100].replace(chr(10), ' ')}", flush=True); time.sleep(min(60, 15 * (attempt + 1)))
                else:
                    raise RuntimeError(r.text[:300])
                vecs.extend(e["values"] for e in r.json()["embeddings"])
                if (i // 100) % 50 == 0: print(f"  {i + len(batch):,}/{len(texts):,}", flush=True)
        X = np.array(vecs, dtype=np.float32)
        return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    N = embed(n_texts, "RETRIEVAL_DOCUMENT"); I = embed(i_texts, "RETRIEVAL_QUERY") if i_texts else np.zeros((0, N.shape[1]), dtype=np.float32)
else:
    import torch
    from sentence_transformers import SentenceTransformer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(name, device=dev, model_kwargs={"torch_dtype": torch.float16} if dev == "cuda" else {})
    m.max_seq_length = 512
    N = m.encode(n_texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    q = [qprefix + t for t in i_texts] if qprefix else i_texts
    I = m.encode(q, batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False) if i_texts else np.zeros((0, N.shape[1]), dtype=np.float32)
np.savez_compressed(out, keys=np.array(keys), N=N.astype(np.float32), texts=np.array(i_texts, dtype=object), I=I.astype(np.float32))
print(f"done {key}: dim {N.shape[1]}, {time.time() - t0:.0f}s → {out}", flush=True)
