import { Badge } from "@/components/ui/badge";
import { amendmentNo } from "@/lib/utils";

/** 정정공고 차수 배지 — 원공고(000)면 아무것도 안 그림 */
export function AmendmentBadge({ ord }: { ord: string | null | undefined }) {
  const n = amendmentNo(ord);
  if (n === null) return null;
  return (
    <Badge
      variant="outline"
      className="border-amber-400 bg-amber-50 text-amber-900 font-bold"
      title={`원공고가 ${n}회 정정됐어요. 변경된 내용은 나라장터 원문에서 확인하세요`}
    >
      정정 {n}차
    </Badge>
  );
}
