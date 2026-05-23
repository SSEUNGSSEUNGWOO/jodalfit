import { Building2, MapPin, Briefcase } from "lucide-react";
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
    <section
      className={cn(
        "inset-card overflow-hidden",
        className
      )}
      aria-label="검색한 회사 정보"
    >
      <div className="flex items-start justify-between gap-4 px-6 py-5 sm:px-7">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-teal-600" aria-hidden />
            <span className="eyebrow text-teal-700">검색한 회사</span>
          </div>
          <h2 className="mt-2 text-[24px] font-bold tracking-tight text-ink-strong leading-tight sm:text-[26px]">
            {company.corp_nm}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px] text-ink-muted">
            <span className="tabular">사업자 {maskBizrno(company.bizrno)}</span>
            {company.rgn_nm && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" aria-hidden /> {company.rgn_nm}
              </span>
            )}
            {company.corp_bsns_div_nm && (
              <span className="flex items-center gap-1">
                <Briefcase className="h-3 w-3" aria-hidden />{" "}
                {company.corp_bsns_div_nm}
              </span>
            )}
          </div>
        </div>

        {/* Activity numbers, if available */}
        {meta && (meta.contractCount || meta.totalAmount) && (
          <div className="hidden sm:flex items-stretch gap-6 border-l border-line pl-6">
            {meta.contractCount !== undefined && (
              <div>
                <div className="eyebrow">누적 수주</div>
                <div className="mt-0.5 text-[22px] font-bold tabular text-navy leading-none">
                  {meta.contractCount}
                  <span className="ml-1 text-[12px] font-medium text-ink-muted">건</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {meta?.primarySectors && meta.primarySectors.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-line bg-bg-alt/40 px-6 py-3 sm:px-7">
          <span className="eyebrow text-ink-muted mr-1">주력 영역</span>
          {meta.primarySectors.map((s) => (
            <span
              key={s}
              className="rounded-tile bg-surface border border-line px-2 py-0.5 text-[12px] font-medium text-ink"
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
