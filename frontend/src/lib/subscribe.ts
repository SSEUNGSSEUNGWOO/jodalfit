"use server";

import { getServerSupabase } from "@/lib/supabase-server";

/**
 * 주간 메일 웨이팅리스트 등록.
 *
 * 발송 파이프라인은 아직 없다. 신청을 실제로 저장하기만 하며,
 * 화면 문구도 "발송 전"이라는 사실을 그대로 말해야 한다.
 */
export async function subscribeToWaitlist(
  email: string,
  bizrnoNorm: string | null
): Promise<{ ok: boolean }> {
  const trimmed = email.trim().toLowerCase();
  if (!trimmed.includes("@") || trimmed.length > 254) return { ok: false };

  const { error } = await getServerSupabase()
    .from("email_subscribers")
    .insert({ email: trimmed, bizrno_norm: bizrnoNorm });

  // 23505 = unique_violation. 이미 신청한 주소이므로 사용자에겐 성공이다.
  if (error && error.code !== "23505") return { ok: false };
  return { ok: true };
}
