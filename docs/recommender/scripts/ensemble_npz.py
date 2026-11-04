"""두 임베딩 npz 를 이어 붙여(각각 L2 정규화 후 concat × 가중치) 앙상블 npz 를 만든다 — 코사인이 두 모델 유사도의 가중 평균이 된다.
사용: python ensemble_npz.py a.npz b.npz out.npz [w_a=0.5]
"""
import sys
import numpy as np

a, b, out = sys.argv[1], sys.argv[2], sys.argv[3]
wa = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
za, zb = np.load(a, allow_pickle=True), np.load(b, allow_pickle=True)
assert za["keys"].tolist() == zb["keys"].tolist() and za["texts"].tolist() == zb["texts"].tolist(), "키·텍스트 순서가 다르다"


def norm(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


N = np.concatenate([np.sqrt(wa) * norm(za["N"]), np.sqrt(1 - wa) * norm(zb["N"])], axis=1)
I = np.concatenate([np.sqrt(wa) * norm(za["I"]), np.sqrt(1 - wa) * norm(zb["I"])], axis=1) if len(za["I"]) else np.zeros((0, N.shape[1]), dtype=np.float32)
np.savez_compressed(out, keys=za["keys"], N=N.astype(np.float32), texts=za["texts"], I=I.astype(np.float32))
print(f"ensemble {a} ({wa}) + {b} ({1 - wa:.2f}) → {out} dim {N.shape[1]}")
