import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { daysUntil, formatKRW } from "@/lib/utils";
import type { NoticeSummary } from "@/lib/notice";

interface Props {
  notice: NoticeSummary;
  rank: number;
}

function ddayLabel(d: number | null) {
  if (d == null) return null;
  if (d < 0) return "마감";
  if (d === 0) return "D-Day";
  return `D-${d}`;
}

function ddayTone(d: number | null) {
  if (d == null) return "text-muted-foreground";
  if (d <= 2) return "text-red-600 font-bold";
  if (d <= 5) return "text-amber-600 font-semibold";
  return "text-muted-foreground";
}

export function SlimNoticeRow({ notice, rank }: Props) {
  const d = daysUntil(notice.bid_clse_date);
  const dlabel = ddayLabel(d);
  const instt = notice.dmnd_instt_nm || notice.ntce_instt_nm || "—";
  const price = formatKRW(notice.presmpt_prce ?? notice.asign_bdgt_amt);

  return (
    <Link
      href={`/notices/${notice.bid_ntce_no}`}
      className="group grid grid-cols-[28px_1fr_auto] gap-3 items-center px-3 py-3 rounded-md border border-transparent hover:border-border hover:bg-muted/30 transition-colors"
    >
      <span className="tabular-nums text-[12px] font-bold text-muted-foreground text-right">
        {rank}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {notice.bsns_div_nm && (
            <Badge variant="secondary" className="text-[10.5px] font-semibold shrink-0">
              {notice.bsns_div_nm}
            </Badge>
          )}
          <span className="text-[14px] font-semibold text-foreground truncate group-hover:text-primary">
            {notice.bid_ntce_nm}
          </span>
        </div>
        <div className="mt-1 text-[12px] text-muted-foreground truncate">{instt}</div>
      </div>
      <div className="flex items-center gap-4 text-[12.5px] tabular-nums shrink-0">
        {dlabel && <span className={ddayTone(d)}>{dlabel}</span>}
        <span className="text-foreground/80 w-[60px] text-right">{price}</span>
      </div>
    </Link>
  );
}
