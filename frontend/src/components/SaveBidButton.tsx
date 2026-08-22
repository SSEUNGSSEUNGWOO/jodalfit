"use client";

import { Bookmark } from "lucide-react";
import { bidKey } from "@/components/board/BoardRow";
import { Button } from "@/components/ui/button";
import { emitNoticeEvent } from "@/lib/events";
import { useShortlist } from "@/lib/shortlist";
import { cn } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";

/**
 * 검토 인장(저장) 버튼.
 *
 * BidCard는 서버 컴포넌트라 onClick을 붙일 수 없어서 이 버튼만 클라이언트로 분리했다.
 * 저장 자체는 localStorage(useShortlist)에 남고, 홈 board와 같은 목록을 공유한다.
 */
export function SaveBidButton({
  bid,
  rank,
  targetBizrno = null,
  algorithmVersion,
}: {
  bid: BidRecommendation;
  rank?: number;
  /** 어느 회사 페이지에서 저장했는지 (이벤트 로깅용) */
  targetBizrno?: string | null;
  algorithmVersion?: string;
}) {
  const { has, toggle } = useShortlist();
  const k = bidKey(bid);
  const saved = has(k);

  const onClick = () => {
    // 홈 board와 동일하게 저장할 때만 기록한다(해제는 안 남김).
    if (!saved) {
      emitNoticeEvent({
        event_type: "save",
        bid_ntce_no: bid.bid_ntce_no,
        bid_ntce_ord: bid.bid_ntce_ord,
        target_bizrno: targetBizrno,
        rank_position: rank,
        algorithm_version: algorithmVersion,
        score: bid.score,
      });
    }
    toggle({
      k,
      bid_ntce_no: bid.bid_ntce_no,
      bid_ntce_ord: bid.bid_ntce_ord,
      bid_ntce_nm: bid.bid_ntce_nm,
      bid_clse_date: bid.bid_clse_date,
    });
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={saved ? "저장 해제" : "저장"}
      aria-pressed={saved}
      onClick={onClick}
    >
      <Bookmark
        className={cn("h-4 w-4", saved && "fill-current text-primary")}
      />
    </Button>
  );
}
