"use client";

import { useState } from "react";
import { Check, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
    setTimeout(() => setStatus("done"), 600);
  };

  if (variant === "inline") {
    return (
      <form onSubmit={submit} className={cn("flex gap-2", className)}>
        <Input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="회사 이메일"
        />
        <Button type="submit" disabled={status !== "idle"}>
          {status === "done" ? "완료" : status === "submitting" ? "..." : "구독"}
        </Button>
      </form>
    );
  }

  return (
    <Card
      className={cn(
        "overflow-hidden bg-primary/5 border-primary/15",
        className
      )}
    >
      <CardContent className="grid gap-7 px-7 py-8 sm:grid-cols-[1.3fr_1fr] sm:items-center sm:px-10 sm:py-10">
        <div>
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-primary" aria-hidden />
            <span className="text-[12.5px] font-bold text-primary">주간 추천 메일</span>
          </div>
          <h3 className="mt-3 text-[24px] sm:text-[28px] font-extrabold leading-tight tracking-tight text-foreground">
            매주 월요일 아침,
            <br />
            우리 회사 공고만 묶어서.
          </h3>
          <p className="mt-2 text-[14.5px] leading-relaxed text-muted-foreground">
            검색한 회사의 과거 낙찰 이력 기준 신규 공고 TOP 5를 메일로 보내드려요.
            언제든 한 번에 구독 해지할 수 있어요.
          </p>
        </div>

        {status === "done" ? (
          <div className="flex items-center gap-3 rounded-xl bg-background border border-primary/15 px-5 py-5">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Check className="h-4 w-4" aria-hidden strokeWidth={3} />
            </span>
            <div className="text-[14px]">
              <div className="font-bold text-foreground">구독 신청 완료</div>
              <div className="text-muted-foreground">다음 월요일부터 메일을 받을 수 있어요.</div>
            </div>
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <Label htmlFor="email-capture">회사 이메일</Label>
            <Input
              id="email-capture"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.co.kr"
              className="h-12 text-[15px]"
            />
            <Button
              type="submit"
              disabled={status !== "idle"}
              size="lg"
              className="h-12 text-[15px]"
            >
              {status === "submitting" ? "처리 중..." : "주간 추천 메일 받기"}
            </Button>
            <p className="text-[12px] text-muted-foreground">
              회원가입 없음 · 마케팅 메일 발송하지 않아요.
            </p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
