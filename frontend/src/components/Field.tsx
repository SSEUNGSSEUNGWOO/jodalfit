// frontend/src/components/Field.tsx
"use client";

import { useId, useState, type ComponentProps, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const INPUT = "h-[46px] w-full rounded-[8px] border border-field bg-panel px-3.5 text-[16px] text-ink outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-ph focus:border-orange focus:shadow-[0_0_0_4px_var(--color-orange-ring)] disabled:bg-paper disabled:text-ink-mute";

export function TextField({ label, hint, right, className, id, ...input }: { label: ReactNode; hint?: ReactNode; right?: ReactNode; className?: string } & ComponentProps<"input">) {
  const auto = useId(); const inputId = id ?? auto;
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between"><label htmlFor={inputId} className="t-k">{label}</label>{right}</div>
      <input id={inputId} className={INPUT} {...input} />
      {hint && <div className="mt-1.5 text-[12.5px] leading-[1.55] text-ink-dim">{hint}</div>}
    </div>
  );
}

/** 비밀번호 — 오른쪽 '표시/숨김'. 8자 미만일 때만 "8자 이상" 힌트(주황 괘선). */
export function PasswordField({ label = "비밀번호", min = 8, showMinHint = true, right, className, id, value, ...input }: { label?: ReactNode; min?: number; showMinHint?: boolean; right?: ReactNode; className?: string; value: string } & Omit<ComponentProps<"input">, "type" | "value">) {
  const auto = useId(); const inputId = id ?? auto;
  const [show, setShow] = useState(false);
  const short = showMinHint && value.length > 0 && value.length < min;
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between"><label htmlFor={inputId} className="t-k">{label}</label>{right}</div>
      <div className="relative">
        <input id={inputId} type={show ? "text" : "password"} value={value} className={cn(INPUT, "pr-14")} {...input} />
        <button type="button" onClick={() => setShow((v) => !v)} aria-pressed={show} aria-controls={inputId}
          className="absolute right-3 top-1/2 -translate-y-1/2 border-b border-line text-[12.5px] text-ink-g">{show ? "숨김" : "표시"}</button>
      </div>
      {short && <div className="mt-1.5 border-l-2 border-orange pl-2 text-[12.5px] text-ink">{min}자 이상</div>}
    </div>
  );
}
