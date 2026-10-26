"use client";

import { useId, useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { TextField } from "@/components/Field";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const KINDS = [
  { v: "idea", label: "의견" },
  { v: "question", label: "문의" },
  { v: "bug", label: "오류 제보" },
] as const;
type Kind = (typeof KINDS)[number]["v"];

export function FeedbackForm({ initialEmail, page }: { initialEmail: string; page: string | null }) {
  const [kind, setKind] = useState<Kind>("idea");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState(initialEmail);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const areaId = useId();
  const ok = message.trim().length >= 5 && !busy;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); if (!ok) return;
    setBusy(true); setErr(null);
    const website = (new FormData(e.currentTarget).get("website") as string) || "";
    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, message: message.trim(), email: email.trim() || null, page, website }),
      });
      if (!res.ok) throw new Error(String(res.status));
      setDone(true);
    } catch {
      setErr("보내지 못했습니다. 잠시 뒤 다시 보내거나 jsw7980@gmail.com 으로 보내 주시면 됩니다.");
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div data-feedback-done className="text-[14.5px] leading-[1.7] text-ink-body">
        <p className="m-0 text-[18px] font-semibold tracking-[-0.02em] text-ink">받았습니다.</p>
        <p className="m-0 mt-2">운영자가 읽습니다. 답이 필요한 내용이면 적어 주신 이메일로 회신합니다.</p>
        <div className="mt-5 flex gap-2"><Btn href="/">입구로</Btn></div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate>
      <p className="mb-[18px] border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink-g">불편한 점, 틀린 정보, 있었으면 하는 기능을 적어 주시면 운영자가 읽습니다.</p>
      <fieldset className="m-0 border-0 p-0">
        <legend className="t-k mb-1.5">종류</legend>
        <div className="flex flex-wrap gap-2" role="radiogroup">
          {KINDS.map((k) => (
            <label key={k.v} className={cn("cursor-pointer rounded-[8px] border px-3.5 py-2 text-[14px] transition-colors", kind === k.v ? "border-ink text-ink" : "border-field text-ink-g hover:border-ink")}>
              <input type="radio" name="kind" value={k.v} checked={kind === k.v} onChange={() => setKind(k.v)} className="sr-only" />
              {k.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="mt-4">
        <div className="mb-1.5 flex items-baseline justify-between"><label htmlFor={areaId} className="t-k">내용</label><span className="num text-[12px] text-ink-mute">{message.length} / 2000</span></div>
        <textarea id={areaId} value={message} onChange={(e) => setMessage(e.target.value.slice(0, 2000))} rows={6} required minLength={5}
          placeholder="예: 회사 검색 결과에 다른 지역 공고가 섞입니다."
          className="w-full rounded-[8px] border border-field bg-panel px-3.5 py-3 text-[16px] leading-[1.6] text-ink outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-ph focus:border-orange focus:shadow-[0_0_0_4px_var(--color-orange-ring)]" />
      </div>
      <TextField className="mt-3.5" label="답장받을 이메일 (선택)" type="email" autoComplete="email" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.co.kr" hint="답이 필요한 문의만 적습니다. 다른 용도로 쓰지 않습니다." />
      {/* 허니팟 — 사람에게는 보이지 않고 봇은 채운다 */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden"><label>website<input name="website" type="text" tabIndex={-1} autoComplete="off" /></label></div>
      {err && <p role="alert" className="mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">보내기</Btn>
      <p className="mt-3.5 text-[12.5px] leading-[1.6] text-ink-dim">기업 정보 비공개 요청은 <a href="/privacy#company-optout" className="u-link text-ink">개인정보처리방침</a>의 절차를 따릅니다.</p>
    </form>
  );
}
