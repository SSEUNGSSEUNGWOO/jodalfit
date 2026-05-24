import { Check, Calendar, FileText, MessageSquare, Megaphone, Award, FileSignature } from "lucide-react";
import { cn, formatDateKR, formatKRW } from "@/lib/utils";
import type { NoticeLifecycle } from "@/lib/notice";

interface Stage {
  key: "plan" | "spec" | "opinion" | "notice" | "award" | "contract";
  label: string;
  sub: string;
  icon: React.ReactNode;
  active: boolean;
  done: boolean;
  count?: number;
  detail?: string;
}

export function Lifecycle({ data }: { data: NoticeLifecycle }) {
  const today = new Date();
  const ntceDt = data.notice.bid_ntce_date
    ? new Date(data.notice.bid_ntce_date)
    : null;
  const clseDt = data.notice.bid_clse_date
    ? new Date(data.notice.bid_clse_date)
    : null;

  const noticeActive = ntceDt !== null && (!clseDt || today <= clseDt);
  const noticeDone = clseDt !== null && today > clseDt;

  const stages: Stage[] = [
    {
      key: "plan",
      label: "발주 계획",
      sub: "사전 공개",
      icon: <Calendar className="h-3.5 w-3.5" />,
      active: data.orderPlans.length > 0 && !data.preSpecs.length,
      done: data.orderPlans.length > 0,
      count: data.orderPlans.length,
      detail: data.orderPlans[0]?.order_year
        ? `${data.orderPlans[0].order_year}.${data.orderPlans[0].order_mnth ?? "—"} 발주 예정`
        : undefined,
    },
    {
      key: "spec",
      label: "사전 규격",
      sub: "사양서 공개",
      icon: <FileText className="h-3.5 w-3.5" />,
      active: data.preSpecs.length > 0 && !noticeActive && !noticeDone,
      done: data.preSpecs.length > 0,
      count: data.preSpecs.length,
      detail: data.preSpecs[0]?.rgst_dt
        ? formatDateKR(data.preSpecs[0].rgst_dt.split(" ")[0])
        : undefined,
    },
    {
      key: "opinion",
      label: "의견 수렴",
      sub: "참여 업체 의견",
      icon: <MessageSquare className="h-3.5 w-3.5" />,
      active: data.opinions.length > 0 && !noticeActive && !noticeDone,
      done: data.opinions.length > 0,
      count: data.opinions.length,
    },
    {
      key: "notice",
      label: "입찰 공고",
      sub: "본 공고 게시",
      icon: <Megaphone className="h-3.5 w-3.5" />,
      active: noticeActive,
      done: noticeDone || data.awards.length > 0 || data.contracts.length > 0,
      detail: data.notice.bid_clse_date
        ? `마감 ${formatDateKR(data.notice.bid_clse_date)}`
        : undefined,
    },
    {
      key: "award",
      label: "낙찰",
      sub: "개찰 / 낙찰자 결정",
      icon: <Award className="h-3.5 w-3.5" />,
      active: data.awards.length > 0 && data.contracts.length === 0,
      done: data.awards.length > 0,
      count: data.awards.length,
      detail: data.awards[0]?.corp_nm
        ? `${data.awards[0].corp_nm}${
            data.awards[0].bid_amt
              ? ` · ${formatKRW(data.awards[0].bid_amt)}`
              : ""
          }`
        : undefined,
    },
    {
      key: "contract",
      label: "계약 체결",
      sub: "최종 계약",
      icon: <FileSignature className="h-3.5 w-3.5" />,
      active: false,
      done: data.contracts.length > 0,
      count: data.contracts.length,
      detail: data.contracts[0]?.cntrct_cncls_date
        ? formatDateKR(data.contracts[0].cntrct_cncls_date)
        : undefined,
    },
  ];

  return (
    <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {stages.map((s, i) => (
        <li key={s.key} className="relative">
          {/* Connector line — between cards on lg */}
          {i < stages.length - 1 && (
            <div
              aria-hidden
              className={cn(
                "hidden lg:block absolute top-[18px] left-full w-3 h-[2px] -translate-y-1/2",
                s.done && stages[i + 1].done
                  ? "bg-primary"
                  : "bg-border"
              )}
            />
          )}

          <div
            className={cn(
              "h-full rounded-xl border p-3 sm:p-4 transition-colors",
              s.active
                ? "border-primary bg-primary/5"
                : s.done
                  ? "border-primary/40 bg-background"
                  : "border-border bg-muted/30"
            )}
          >
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold",
                  s.done
                    ? "bg-primary text-primary-foreground"
                    : s.active
                      ? "bg-primary/15 text-primary"
                      : "bg-muted text-muted-foreground"
                )}
              >
                {s.done ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : s.icon}
              </div>
              <div className="text-[10.5px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                STEP {String(i + 1).padStart(2, "0")}
              </div>
            </div>

            <div className="mt-3">
              <div
                className={cn(
                  "text-[14px] font-bold",
                  s.done || s.active ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {s.label}
              </div>
              <div className="text-[11.5px] text-muted-foreground mt-0.5">
                {s.sub}
              </div>
              {s.count !== undefined && s.done && (
                <div className="mt-2 text-[11.5px] font-bold text-primary">
                  {s.count}건
                </div>
              )}
              {s.detail && (
                <div className="mt-2 text-[11px] text-foreground/70 leading-[1.5]">
                  {s.detail}
                </div>
              )}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
