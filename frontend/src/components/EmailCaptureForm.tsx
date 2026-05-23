"use client";

import { useState } from "react";
import { Mail, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmailCaptureForm({
  className,
  variant = "panel",
}: {
  className?: string;
  variant?: "panel" | "inline";
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "done">("idle");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setStatus("submitting");
    // TODO: hook backend subscribers
    setTimeout(() => setStatus("done"), 600);
  };

  if (variant === "inline") {
    return (
      <form
        onSubmit={submit}
        className={cn(
          "flex flex-col gap-2 sm:flex-row sm:items-center",
          className
        )}
      >
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="회사 이메일"
          className="flex-1 rounded-tile border border-line bg-surface px-3 py-2.5 text-[14px] outline-none transition-colors focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={status !== "idle"}
          className="rounded-tile bg-navy px-4 py-2.5 text-[13.5px] font-semibold text-white transition-colors hover:bg-navy-700 disabled:opacity-50"
        >
          {status === "done" ? "구독 완료" : status === "submitting" ? "처리 중..." : "구독하기"}
        </button>
      </form>
    );
  }

  return (
    <div
      className={cn(
        "relative overflow-hidden inset-card",
        className
      )}
    >
      <div className="relative grid gap-6 px-7 py-8 sm:grid-cols-[1.4fr_1fr] sm:items-center sm:px-10 sm:py-10">
        <div>
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-teal-600" aria-hidden />
            <span className="eyebrow text-teal-700">주간 추천 메일</span>
          </div>
          <h3 className="mt-3 text-[22px] font-bold leading-snug tracking-tight text-ink-strong sm:text-[26px]">
            매주 월요일 아침,<br />
            우리 회사에 맞는 공고만 받아보세요.
          </h3>
          <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">
            검색한 회사의 과거 낙찰 이력 기준 신규 공고 TOP 5를 메일로 보내드립니다.
            언제든 한 번에 구독 해지할 수 있습니다.
          </p>
        </div>

        {status === "done" ? (
          <div className="flex items-center gap-3 rounded-card border border-teal-300 bg-teal-50 px-5 py-5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-500 text-white">
              <Check className="h-4 w-4" aria-hidden strokeWidth={3} />
            </span>
            <div className="text-[14px]">
              <div className="font-semibold text-teal-700">구독 신청 완료</div>
              <div className="text-ink-muted">다음 월요일부터 메일을 받으실 수 있습니다.</div>
            </div>
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-2">
            <label htmlFor="email-capture" className="eyebrow text-ink-muted">
              회사 이메일
            </label>
            <input
              id="email-capture"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.co.kr"
              className="rounded-tile border border-line bg-surface px-4 py-3 text-[15px] outline-none transition-colors focus:border-navy"
            />
            <button
              type="submit"
              disabled={status !== "idle"}
              className="mt-1 rounded-tile bg-navy px-4 py-3 text-[14px] font-semibold text-white transition-colors hover:bg-navy-700 disabled:opacity-50"
            >
              {status === "submitting" ? "처리 중..." : "주간 추천 메일 받기"}
            </button>
            <p className="mt-1 text-[12px] text-ink-soft">
              회원가입 절차 없음 · 광고/마케팅 메일 발송하지 않습니다.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
