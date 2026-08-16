"use client";

import { useState } from "react";

/** 주간 브리핑 구독대 — 네이비 밴드. 자동 구독 백엔드가 없어 신청은 메일로 정직하게 접수. */
export function SubscribeBand() {
  const [email, setEmail] = useState("");
  const [opened, setOpened] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    const subject = encodeURIComponent("조달핏 주간 브리핑 구독 신청");
    const body = encodeURIComponent(`구독 이메일: ${email}`);
    window.location.href = `mailto:jsw7980@gmail.com?subject=${subject}&body=${body}`;
    setOpened(true);
  };

  return (
    <section className="bg-gc-band">
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 py-9 sm:py-11 grid gap-6 sm:grid-cols-[1.2fr_1fr] sm:items-center">
        <div>
          <h2 className="font-gc-serif font-black text-[23px] sm:text-[27px] leading-[1.35] tracking-[-0.02em] text-gc-band-hi break-keep">
            매주 월요일 아침,
            <br />이 판을 메일로 받아보세요.
          </h2>
          <p className="mt-2.5 text-[13.5px] leading-[1.7] text-gc-band-ink break-keep">
            검색한 회사 기준 신규 공고 TOP 5를 정리해 보냅니다. 회원가입 없음 ·
            언제든 한 번에 해지.
          </p>
        </div>
        <div>
          {opened ? (
            <p className="text-[14px] font-bold text-gc-band-hi break-keep">
              메일 앱이 열렸습니다 — 신청 메일을 보내주시면 다음 월요일부터
              보내드립니다.
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
                className="shrink-0 h-11 px-4 bg-gc-band-hi text-gc-band text-[14px] font-bold rounded-[3px] hover:bg-white transition-colors"
              >
                주간 브리핑 받기
              </button>
            </form>
          )}
          {!opened && (
            <p className="mt-2 text-[11.5px] text-gc-band-ink">
              신청은 이메일로 접수됩니다 — 버튼을 누르면 메일 앱이 열립니다.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
