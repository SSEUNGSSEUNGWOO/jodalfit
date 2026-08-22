"use client";

import { useState } from "react";
import { Check, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { subscribeToWaitlist } from "@/lib/subscribe";

export function EmailCaptureForm({
  className,
  variant = "panel",
  bizrno = null,
}: {
  className?: string;
  variant?: "panel" | "inline";
  /** 신청이 일어난 회사 페이지. 어느 페이지에서 수요가 나오는지 보려고 함께 저장한다. */
  bizrno?: string | null;
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "done" | "error"
  >("idle");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setStatus("submitting");
    const { ok } = await subscribeToWaitlist(email, bizrno);
    setStatus(ok ? "done" : "error");
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
        <Button
          type="submit"
          disabled={status === "submitting" || status === "done"}
        >
          {status === "done" ? "접수됨" : status === "submitting" ? "..." : "신청"}
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
            <span className="text-[12.5px] font-bold text-primary">
              주간 추천 메일 · 준비 중
            </span>
          </div>
          <h3 className="mt-3 text-[24px] sm:text-[28px] font-extrabold leading-tight tracking-tight text-foreground">
            매주 월요일 아침,
            <br />
            우리 회사 공고만 묶어서.
          </h3>
          <p className="mt-2 text-[14.5px] leading-relaxed text-muted-foreground">
            검색한 회사의 등록업종·공급물품과 수주 이력을 함께 분석한 신규 공고 TOP 5를 메일로 보내드릴 예정이에요.
            아직 발송 전이라, 첫 메일이 준비되면 신청하신 주소로 알려드릴게요.
          </p>
        </div>

        {status === "done" ? (
          <div className="flex items-center gap-3 rounded-xl bg-background border border-primary/15 px-5 py-5">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Check className="h-4 w-4" aria-hidden strokeWidth={3} />
            </span>
            <div className="text-[14px]">
              <div className="font-bold text-foreground">신청 접수됨</div>
              <div className="text-muted-foreground">
                첫 발송이 준비되면 이 주소로 알려드릴게요.
              </div>
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
              disabled={status === "submitting"}
              size="lg"
              className="h-12 text-[15px]"
            >
              {status === "submitting" ? "처리 중..." : "발송 시작하면 알려주세요"}
            </Button>
            {status === "error" && (
              <p className="text-[12px] text-destructive">
                신청을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.
              </p>
            )}
            <p className="text-[12px] text-muted-foreground">
              회원가입 없음 · 아직 발송 전이에요.
            </p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
