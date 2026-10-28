// frontend/src/lib/after-auth.ts
// 로그인·가입 확인·OAuth 콜백 뒤 어디로 보낼지 — 세 길이 같은 규칙을 쓴다(2026-10-28).
//   1) 동의가 비어 있으면(OAuth 가입은 가입 폼을 안 거친다 → 0052 트리거가 ''/'' 행을 만든다) /consent 로. 동의 뒤 갈 곳을 next 에 품는다.
//   2) 저장 회사 0곳이고 next 에 회사가 없으면 /welcome 으로(가입 때만 — 로그인은 그대로 next).
import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";

const HAS_COMPANY = /\/companies\/|[?&]company=/;

export async function afterAuthDestination(supabase: SupabaseClient, next: string, { signup }: { signup: boolean }): Promise<string> {
  let dest = next;
  if (signup && !HAS_COMPANY.test(next)) {
    const { data } = await supabase.from("saved_companies").select("bizrno_norm").limit(1);
    if (!data?.length) dest = `/welcome?next=${encodeURIComponent(next)}`;
  }
  const { data: consent } = await supabase.from("user_consents").select("terms_version").maybeSingle();
  if (consent && consent.terms_version === "") dest = `/consent?next=${encodeURIComponent(dest)}`;
  return dest;
}
