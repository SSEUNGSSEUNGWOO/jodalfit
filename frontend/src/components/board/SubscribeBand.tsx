"use client";

import { useState } from "react";
import { subscribeToWaitlist } from "@/lib/subscribe";

/**
 * 주간 브리핑 구독대 — 네이비 밴드.
 * 발송 파이프라인은 아직 없다. 예전엔 mailto로 신청을 받았는데 메일 앱을 열어야 해
 * 마찰이 컸고 신청이 어디에도 집계되지 않았다. 지금은 회사 페이지의
 * EmailCaptureForm과 같은 웨이팅리스트에 저장한다.
 */
export function SubscribeBand() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "done" | "error"
  >("idle");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setStatus("submitting");
    // 홈·목록에서 뜨는 밴드라 특정 회사 페이지가 없다.
    const { ok } = await subscribeToWaitlist(email, null);
    setStatus(ok ? "done" : "error");
  };

  return (
    <section className="bg-gc-band">
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 py-9 sm:py-11 grid gap-6 sm:grid-cols-[1.2fr_1fr] sm:items-center">
        <div>
          <p className="text-[12px] font-bold text-gc-band-ink">주간 브리핑 · 준비 중</p>
          <h2 className="mt-1.5 font-gc-serif font-black text-[23px] sm:text-[27px] leading-[1.35] tracking-[-0.02em] text-gc-band-hi break-keep">
            매주 월요일 아침,
            <br />이 판을 메일로 받아보세요.
          </h2>
          <p className="mt-2.5 text-[13.5px] leading-[1.7] text-gc-band-ink break-keep">
            검색한 회사의 등록업종·공급물품과 수주 이력을 함께 분석한 신규 공고 TOP 5를
            보내드릴 예정이에요. 아직 발송 전이라, 준비되면 신청하신 주소로 알려드릴게요.
          </p>
        </div>
        <div>
          {status === "done" ? (
            <p className="text-[14px] font-bold text-gc-band-hi break-keep">
              신청 접수됨 — 첫 발송이 준비되면 이 주소로 알려드릴게요.
            </p>
          ) : (
            <form onSubmit={submit} className="flex gap-2">
              <label htmlFor="gc-subscribe" className="sr-only">
                회사 이메일
              </label>
              <input
                id="gc-subscribe"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.co.kr"
                className="flex-1 h-11 bg-gc-sheet border border-gc-tint-line rounded-[3px] px-3.5 text-[14.5px] font-medium text-gc-ink placeholder:text-gc-ink-3 outline-none focus:border-gc-ink transition-colors min-w-0"
              />
              <button
                type="submit"
                disabled={status === "submitting"}
                className="shrink-0 h-11 px-4 bg-gc-band-hi text-gc-band text-[14px] font-bold rounded-[3px] hover:bg-white transition-colors disabled:opacity-60"
              >
                {status === "submitting" ? "처리 중..." : "발송 시작하면 알려주세요"}
              </button>
            </form>
          )}
          {status !== "done" && (
            <p className="mt-2 text-[11.5px] text-gc-band-ink">
              {status === "error"
                ? "신청을 저장하지 못했어요. 잠시 후 다시 시도해 주세요."
                : "회원가입 없음 · 아직 발송 전이에요."}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
