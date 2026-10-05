"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { SimilarNotice } from "@/lib/notice";
import { formatDateKR, formatKRW } from "@/lib/utils";

/** 공고 상세 "비슷한 공고" — /api/notices/[bid_ntce_no]/similar 를 브라우저에서 호출.
 *  SSR에 넣지 않는 이유: "오늘 이후 마감"으로 거르므로 결과가 매일 바뀌고, 그러면 내용이 그대로인
 *  공고 페이지도 매일 ISR Write가 난다. robots.txt가 /api/ 를 막으므로 크롤러는 이 링크를 못 본다. */
export function SimilarNotices({ bidNtceNo }: { bidNtceNo: string }) {
  const [similar, setSimilar] = useState<SimilarNotice[] | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/notices/${encodeURIComponent(bidNtceNo)}/similar`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((rows: SimilarNotice[]) => {
        if (alive) setSimilar(rows);
      })
      .catch(() => {
        if (alive) setSimilar([]);
      });
    return () => {
      alive = false;
    };
  }, [bidNtceNo]);

  if (!similar || similar.length === 0) return null;

  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14 border-t border-border">
      <div className="mb-6">
        <h2 className="text-[20px] sm:text-[24px] font-extrabold tracking-tight text-foreground">
          비슷한 공고
        </h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          이 공고와 의미가 가까운 진행 중 공고 {similar.length}건이에요. 마감일이 지난 공고는 자동 제외.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {similar.map((s) => {
          const sim = Math.round(s.similarity * 100);
          return (
            <a
              key={s.bid_ntce_no}
              href={`/notices/${s.bid_ntce_no}`}
              className="block rounded-lg border border-border bg-card p-4 hover:border-primary/40 hover:shadow-sm transition-all"
            >
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-[15px] font-bold text-foreground leading-snug line-clamp-2">
                  {s.bid_ntce_nm}
                </div>
                <span className="shrink-0 text-[11px] font-bold text-primary tabular-nums">
                  유사도 {sim}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted-foreground">
                {s.bsns_div_nm && (
                  <Badge variant="secondary" className="text-[11px]">
                    {s.bsns_div_nm}
                  </Badge>
                )}
                <span className="truncate">
                  {s.dmnd_instt_nm || s.ntce_instt_nm || "—"}
                </span>
                {s.bid_clse_date && (
                  <>
                    <Dot />
                    <span>마감 {formatDateKR(s.bid_clse_date)}</span>
                  </>
                )}
                {s.presmpt_prce != null && (
                  <>
                    <Dot />
                    <span>추정 {formatKRW(s.presmpt_prce)}</span>
                  </>
                )}
              </div>
            </a>
          );
        })}
      </div>
    </section>
  );
}

function Dot() {
  return <span aria-hidden className="text-muted-foreground/50">·</span>;
}
