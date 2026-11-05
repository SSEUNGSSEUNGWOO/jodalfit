/** 임베딩 공간 스위치 — openai(1536d, `embedding`) / kure(1024d, `embedding_k`) / gemini(768d, `embedding_g`).
 *  백엔드 `app/services/embedding.py` 의 SPACES 표와 같은 규칙. 전환은 NEXT_PUBLIC_EMBED_SPACE=kure|gemini. */

/** select 문자열은 supabase-js 가 타입 레벨에서 파싱한다 — 리터럴 분기로 둬야 추론이 살아 있다. */
export const IS_KURE = process.env.NEXT_PUBLIC_EMBED_SPACE === "kure";
export const IS_GEMINI = process.env.NEXT_PUBLIC_EMBED_SPACE === "gemini";

/** 벡터 컬럼 이름. */
export const EMB_COL = IS_KURE ? "embedding_k" : IS_GEMINI ? "embedding_g" : "embedding";

/** 공간에 맞는 RPC 이름 (kure 는 0045 의 `_k`, gemini 는 0067 의 `_g` 변형). */
export function rpcName(base: string): string {
  return IS_KURE ? `${base}_k` : IS_GEMINI ? `${base}_g` : base;
}
