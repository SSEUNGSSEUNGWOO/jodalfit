"use server";

import { getServerSupabase } from "@/lib/supabase-server";
import { PRIVACY_VERSION } from "@/lib/privacy";

/**
 * 주간 메일 웨이팅리스트 등록.
 *
 * 발송 파이프라인은 아직 없다. 신청을 실제로 저장하기만 하며,
 * 화면 문구도 "발송 전"이라는 사실을 그대로 말해야 한다.
 *
 * 개인정보 수집·이용과 광고성 정보 수신 동의를 둘 다 받아야 저장한다(폼이 버튼을 막지만
 * 서버에서도 확인한다). 동의 시각과 처리방침 버전을 같이 남긴다 (0040).
 */
export async function subscribeToWaitlist(
  email: string,
  bizrnoNorm: string | null,
  consent: { privacy: boolean; marketing: boolean }
): Promise<{ ok: boolean }> {
  const trimmed = email.trim().toLowerCase();
  if (!trimmed.includes("@") || trimmed.length > 254) return { ok: false };
  if (!consent.privacy || !consent.marketing) return { ok: false };

  // 같은 주소·회사로 다시 신청하면 동의 기록만 새로 갱신한다.
  const { error } = await getServerSupabase()
    .from("email_subscribers")
    .upsert(
      {
        email: trimmed,
        bizrno_norm: bizrnoNorm,
        consented_at: new Date().toISOString(),
        consent_version: PRIVACY_VERSION,
      },
      { onConflict: "email,bizrno_norm" }
    );

  return { ok: !error };
}
