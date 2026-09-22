"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

export type Consent = { privacy: boolean; marketing: boolean };
export const NO_CONSENT: Consent = { privacy: false, marketing: false };
export const hasConsent = (c: Consent) => c.privacy && c.marketing;

/**
 * 주간 메일 신청 동의 — 개인정보 수집·이용과 광고성 정보 수신은 따로 받는다.
 * 둘 다 체크해야 신청 버튼이 켜지고, 서버(lib/subscribe.ts)도 한 번 더 확인한다.
 */
export function SubscribeConsent({
  value,
  onChange,
  idPrefix,
  tone = "light",
}: {
  value: Consent;
  onChange: (c: Consent) => void;
  idPrefix: string;
  tone?: "light" | "band";
}) {
  const text = tone === "band" ? "text-gc-band-ink" : "text-muted-foreground";
  const link = tone === "band" ? "text-gc-band-hi" : "text-foreground";
  const row = "flex items-start gap-2 text-[12px] leading-[1.55] break-keep";

  return (
    <div className={cn("space-y-1.5", text)}>
      <label htmlFor={`${idPrefix}-privacy`} className={row}>
        <input
          id={`${idPrefix}-privacy`}
          type="checkbox"
          checked={value.privacy}
          onChange={(e) => onChange({ ...value, privacy: e.target.checked })}
          className="mt-[3px] shrink-0"
        />
        <span>
          [필수] 개인정보 수집·이용 동의 — 이메일 주소를 주간 메일 발송에만 쓰고, 해지할 때까지
          보관합니다.{" "}
          <Link href="/privacy" target="_blank" className={cn("underline underline-offset-2", link)}>
            처리방침
          </Link>
        </span>
      </label>
      <label htmlFor={`${idPrefix}-marketing`} className={row}>
        <input
          id={`${idPrefix}-marketing`}
          type="checkbox"
          checked={value.marketing}
          onChange={(e) => onChange({ ...value, marketing: e.target.checked })}
          className="mt-[3px] shrink-0"
        />
        <span>[필수] 광고성 정보 수신 동의 — 주간 추천 메일과 서비스 소식. 언제든 수신을 거부할 수 있습니다.</span>
      </label>
    </div>
  );
}
