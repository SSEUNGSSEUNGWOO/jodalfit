// frontend/src/lib/after-auth.ts
// 로그인·가입 확인·OAuth 콜백 뒤 어디로 보낼지 — 세 길이 같은 규칙을 쓴다(2026-10-28).
//   1) 동의가 비어 있으면(OAuth 가입은 가입 폼을 안 거친다 → 0052 트리거가 ''/'' 행을 만든다) /consent 로. 그 화면이 우리 회사 저장도 같이 받으므로
//      /welcome 을 거치지 않는다(두 번 묻지 않게). 동의 뒤 갈 곳을 next 에 품는다.
//   2) 가입이고 저장 회사 0곳이면 /welcome 으로(로그인은 그대로 next).
//      next 에 회사가 있어도 보낸다(2026-11-09) — 그 전엔 건너뛰었는데, 저장은 가입 직후 그 화면에서만 일어났다(35명 중 13명 저장, 11명이 1분 안).
//      결과 화면으로 돌려보낸 이메일 가입자는 머리의 ☆ 버튼을 못 보고 떠났다(7명 중 저장 2명). /welcome 이 next 의 회사를 읽어 한 번에 저장하게 한다.
import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";

export async function afterAuthDestination(supabase: SupabaseClient, next: string, { signup }: { signup: boolean }): Promise<string> {
  const { data: consent } = await supabase.from("user_consents").select("terms_version").maybeSingle();
  if (consent && consent.terms_version === "") return `/consent?next=${encodeURIComponent(next)}`;
  if (signup) {
    const { data } = await supabase.from("saved_companies").select("bizrno_norm").limit(1);
    if (!data?.length) return `/welcome?next=${encodeURIComponent(next)}`;
  }
  return next;
}
