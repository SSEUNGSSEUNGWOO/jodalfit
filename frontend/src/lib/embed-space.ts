/** 임베딩 공간 스위치 — openai(1536d, `embedding`) / kure(1024d, `embedding_k`).
 *  백엔드 `app/services/recommend.py::_rpc_name/_emb_col` 과 같은 규칙. 전환은 NEXT_PUBLIC_EMBED_SPACE=kure. */

/** select 문자열은 supabase-js 가 타입 레벨에서 파싱한다 — 리터럴 분기로 둬야 추론이 살아 있다. */
export const IS_KURE = process.env.NEXT_PUBLIC_EMBED_SPACE === "kure";

/** 벡터 컬럼 이름. */
export const EMB_COL = IS_KURE ? "embedding_k" : "embedding";

/** 공간에 맞는 RPC 이름 (kure 는 0045 의 `_k` 변형). */
export function rpcName(base: string): string {
  return IS_KURE ? `${base}_k` : base;
}
