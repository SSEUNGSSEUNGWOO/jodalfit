// frontend/src/lib/mail-link.ts
// 주간 메일 "그만 받기" 링크의 토큰 — 로그인 없이 메일 링크만으로 수신 여부를 바꾼다.
// backend/jobs/send_weekly_mail.py::mail_token 과 같은 식: HMAC-SHA256(INTERNAL_API_TOKEN, user_id) 의 앞 32자리.
import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";

function secret(): string | null {
  return process.env.INTERNAL_API_TOKEN || null;
}

export function weeklyMailToken(userId: string): string | null {
  const s = secret();
  if (!s) return null;
  return createHmac("sha256", s).update(userId).digest("hex").slice(0, 32);
}

export function verifyWeeklyMailToken(userId: string, token: string): boolean {
  const want = weeklyMailToken(userId);
  if (!want || !/^[0-9a-f]{32}$/.test(token) || !/^[0-9a-f-]{36}$/.test(userId)) return false;
  return timingSafeEqual(Buffer.from(want), Buffer.from(token));
}
