// frontend/src/components/notice/NoticeRail.tsx
// 공고 상세(07)의 왼쪽 레일 — 마감 · 참가 자격 · 수치 · 첨부 원본.
// 서버 컴포넌트. 자격 판정은 백엔드 /qualifications/check 와 같은 규칙을 쓰고, 회사를 모르면 판정하지 않는다.
import type { BidNotice } from "@/lib/notice";
import { cn } from "@/lib/utils";

const nf = new Intl.NumberFormat("ko-KR");

export type QualLine = { label: string; state: "ok" | "warn" | "none" | "todo"; text: string };

function won(v: number | null | undefined): string {
  if (!v) return "—";
  return v >= 100_000_000 ? `${(v / 100_000_000).toFixed(1)}억` : `${nf.format(Math.round(v / 10_000))}만`;
}

function dLeft(clse: string | null | undefined, today: Date): number | null {
  if (!clse) return null;
  const a = Date.parse(`${clse.slice(0, 10)}T00:00:00+09:00`);
  const b = Date.parse(`${today.toISOString().slice(0, 10)}T00:00:00+09:00`);
  return Number.isNaN(a) ? null : Math.round((a - b) / 86400_000);
}

export function NoticeRail({ n, quals, today }: { n: BidNotice; quals: QualLine[]; today: Date }) {
  const d = dLeft(n.bid_clse_date, today);
  const closed = d != null && d < 0;
  const files = (n.attachments ?? []) as { seq?: number; name?: string; url: string }[];

  return (
    <aside className="sticky top-5 self-start max-sm:static">
      <div className="border-b border-ink pb-2.5">
        <span className="text-[12px] text-ink-g">입찰 마감</span>
        <div className="mt-1 flex items-baseline gap-2">
          {closed ? (
            <b className="text-[22px] font-[650] text-ink-mute">마감</b>
          ) : (
            <b className={cn("num text-[26px] font-[650] tracking-[-0.03em]", d != null && d <= 7 ? "text-orange" : "text-ink")}>
              {d == null ? "—" : `D-${d}`}
            </b>
          )}
          <span className="num text-[13px] text-ink-g">{n.bid_clse_date?.slice(0, 10).replace(/-/g, ".") ?? "—"}</span>
        </div>
      </div>

      <div className="mt-4">
        <span className="text-[12px] text-ink-g">참가 자격</span>
        <ul className="mt-1.5">
          {quals.map((q) => (
            <li key={q.label} className="flex items-baseline gap-2 border-b border-rule-2 py-1.5 text-[13.5px] last:border-0">
              <span className="w-[42px] shrink-0 text-ink-g">{q.label}</span>
              <span className={cn(q.state === "ok" ? "font-[650] text-ink" : q.state === "warn" ? "text-ink" : "text-ink-mute")}>
                {q.text}
                {q.state === "ok" && <span className="ml-1">✓</span>}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11.5px] leading-[1.6] text-ink-mute">
          공고에 적힌 면허·지역·등록 마감만 봅니다. 첨부 문서가 요구하는 실적·증명은 판정하지 않습니다.
        </p>
      </div>

      <div className="mt-4">
        <span className="text-[12px] text-ink-g">수치</span>
        <ul className="mt-1.5 text-[13.5px]">
          {[
            ["추정가", won(n.presmpt_prce)],
            ["배정 예산", won(n.asign_bdgt_amt)],
            ["개찰일", n.openg_date?.slice(0, 10).replace(/-/g, ".") ?? "—"],
            ["계약 방식", n.cntrct_cncls_mthd_nm || "—"],
            ["낙찰자 결정", n.bidwinr_dcsn_mthd_nm || "—"],
          ].map(([k, v]) => (
            <li key={k} className="flex items-baseline justify-between gap-3 border-b border-rule-2 py-1.5 last:border-0">
              <span className="text-ink-g">{k}</span>
              <b className="num font-[650] text-ink">{v}</b>
            </li>
          ))}
        </ul>
      </div>

      {/* 첨부 원본 — 요약이 없을수록 원문이 더 필요하다. 주소는 수집 때 이미 받아 둔 것이다. */}
      {files.length > 0 && (
        <div className="mt-4">
          <span className="text-[12px] text-ink-g">첨부 원본 {files.length}</span>
          <ul className="mt-1.5 text-[13.5px]">
            {files.slice(0, 8).map((f, i) => (
              <li key={f.url} className="border-b border-rule-2 py-1.5 last:border-0">
                <a href={f.url} className="break-all text-ink underline-offset-2 hover:text-orange hover:underline" rel="nofollow noopener">
                  {f.name || `첨부 ${f.seq ?? i + 1}`}
                </a>
              </li>
            ))}
          </ul>
          {files.length > 8 && <p className="mt-1 text-[11.5px] text-ink-mute">외 {files.length - 8}건</p>}
        </div>
      )}

      {n.bid_ntce_url && (
        <a
          href={n.bid_ntce_url}
          rel="nofollow noopener"
          className="mt-4 inline-block rounded-[4px] bg-ink px-3.5 py-2 text-[13.5px] font-[650] text-paper"
        >
          나라장터 원문
        </a>
      )}
    </aside>
  );
}
