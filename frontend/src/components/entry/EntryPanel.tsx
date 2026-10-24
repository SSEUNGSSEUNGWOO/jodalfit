// frontend/src/components/entry/EntryPanel.tsx
// 입구 판 — 현황 숫자 셋 + 최근(또는 오늘) 등록된 공고. 시안 entry-v2 의 D 안.
// 서버 컴포넌트: 값은 lib/entry.ts 가 서버에서 읽어 넘긴다.
import Link from "next/link";
import type { EntryData } from "@/lib/entry";
import { cn } from "@/lib/utils";
import { FreshTicker } from "./FreshTicker";

const nf = new Intl.NumberFormat("ko-KR");

export function EntryPanel({ d }: { d: EntryData }) {
  const stats: { n: number; label: string; hot?: boolean }[] = [
    { n: d.active, label: "지금 입찰 가능한 공고" },
    { n: d.specOpen, label: "의견 접수 중인 사전규격", hot: true },
    { n: d.companies, label: "등록된 회사" },
  ];
  return (
    <div className="mx-auto mt-[26px] max-w-[760px] rounded-[6px] border border-hair bg-panel px-6 py-[22px] max-sm:px-4">
      {/* 세 묶음을 판 양 끝까지 — 아래 공고 목록이 판 전체 폭을 쓰는데 숫자만 왼쪽에 몰려 오른쪽이 비었다 */}
      <div className="flex justify-between gap-[34px] max-sm:flex-wrap max-sm:justify-start max-sm:gap-x-6 max-sm:gap-y-3">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col gap-[3px]">
            <b className={cn("num text-[24px] font-[650] tracking-[-0.03em]", s.hot ? "text-orange-ink" : "text-ink")}>
              {nf.format(s.n)}
            </b>
            <span className="text-[12.5px] text-ink-g">{s.label}</span>
          </div>
        ))}
      </div>

      {d.fresh.length > 0 && (
        <div className="mt-5 border-t border-ink pt-3.5">
          {/* 라벨이 실제 상태를 따라간다 — 오늘 치가 얇으면 '최근'으로. 숫자를 꾸미지 않는다. */}
          <span className="text-[12.5px] text-ink-g">
            {d.freshToday ? `오늘 등록된 공고 ${nf.format(d.todayCount)}건` : "최근 등록된 공고"}
          </span>
          <FreshTicker items={d.fresh} />
          <Link href="/notices" className="mt-3 inline-block border-b border-field text-[13px] text-ink-g hover:border-orange">
            전체 보기 →
          </Link>
        </div>
      )}
    </div>
  );
}
