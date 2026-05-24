import Link from "next/link";
import { Building2, ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn, maskBizrno } from "@/lib/utils";
import type { CompanyDigest } from "@/types/recommendations";

export function CompanyCard({
  company,
  meta,
  className,
}: {
  company: CompanyDigest;
  meta?: {
    contractCount?: number;
    totalAmount?: number;
    primarySectors?: string[];
  };
  className?: string;
}) {
  return (
    <Card className={cn("", className)} aria-label="검색한 회사 정보">
      <CardContent className="p-6 sm:p-7">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" aria-hidden />
              <span className="text-[12.5px] font-bold text-primary">분석 대상</span>
            </div>
            <Link
              href={`/companies/${company.bizrno.replace(/\D/g, "")}`}
              className="group inline-flex items-baseline gap-2 mt-2 hover:text-primary transition-colors"
            >
              <h2 className="text-[26px] sm:text-[28px] font-extrabold tracking-tight text-foreground group-hover:text-primary">
                {company.corp_nm}
              </h2>
              <ArrowUpRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
            <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px] text-muted-foreground">
              <span className="tabular tabular-nums font-medium">
                사업자 {maskBizrno(company.bizrno)}
              </span>
              {company.rgn_nm && (
                <>
                  <Dot />
                  <span>{company.rgn_nm}</span>
                </>
              )}
              {company.corp_bsns_div_nm && (
                <>
                  <Dot />
                  <span>{company.corp_bsns_div_nm}</span>
                </>
              )}
            </div>
          </div>

          {meta?.contractCount !== undefined && (
            <div className="flex items-baseline gap-1.5 bg-muted rounded-xl px-4 py-3">
              <span className="text-[28px] font-extrabold tabular tabular-nums text-primary leading-none">
                {meta.contractCount}
              </span>
              <span className="text-[13px] font-semibold text-foreground/70">
                건 수주
              </span>
            </div>
          )}
        </div>

        {meta?.primarySectors && meta.primarySectors.length > 0 && (
          <div className="mt-5 pt-4 border-t flex flex-wrap items-center gap-1.5">
            <span className="text-[12.5px] font-semibold text-muted-foreground mr-1">
              주력 영역
            </span>
            {meta.primarySectors.map((s) => (
              <Badge key={s} variant="secondary" className="font-medium">
                {s}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Dot() {
  return (
    <span aria-hidden className="text-muted-foreground/40">
      ·
    </span>
  );
}
