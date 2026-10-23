// 선별 과정은 접힌 한 줄로 두고, 단계 설명은 펼쳐서 확인한다.
import { cn } from "@/lib/utils";
import { FUNNEL_LABELS, type SceneCounts } from "./Scene";

const fmt = (n: number | null) => (n == null ? "…" : n.toLocaleString("ko-KR"));

export function FunnelLine({ counts, open }: { counts: SceneCounts; open: boolean }) {
  const nums = [counts.total, counts.candidates, counts.passed, counts.results];
  return (
    <details data-funnel hidden={!open} className="group border-b border-hair text-[13px] text-ink-g">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-1 py-2 [&::-webkit-details-marker]:hidden">
        <span className="font-medium">선별 과정</span>
        <span className="num flex items-center gap-2.5" aria-label="전체 공고, 유사 후보, 자격 통과, 추천 결과 순">
          {nums.map((n, i) => (
            <span key={i} className="flex items-center gap-2.5">
              {i > 0 && <span aria-hidden="true" className="text-ink-off">→</span>}
              <b data-n={i} className={cn("font-semibold", i === 3 ? "text-orange-ink" : "text-ink-g")}>{fmt(n)}</b>
            </span>
          ))}
        </span>
        <span className="ml-auto text-[12px] text-ink-dim"><span className="group-open:hidden">과정 보기 +</span><span className="hidden group-open:inline">접기 −</span></span>
      </summary>
      <ol className="mb-3 grid grid-cols-4 gap-4 border-t border-hair pt-3 max-sm:grid-cols-2">
        {FUNNEL_LABELS.map((label, i) => (
          <li key={label}><span className="mb-1 block text-[11px] text-ink-mute">0{i + 1}</span><span className="block break-keep text-[12px]">{label}</span><strong className="num mt-1 block text-[17px] font-semibold text-ink">{fmt(nums[i])}</strong></li>
        ))}
      </ol>
    </details>
  );
}
