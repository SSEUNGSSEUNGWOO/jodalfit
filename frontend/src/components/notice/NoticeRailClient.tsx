// frontend/src/components/notice/NoticeRailClient.tsx
// 레일을 클라이언트에서 그린다 — D-day 는 '오늘'에 의존하는데, 서버 출력에 오늘이 들어가면
// 매일 출력이 달라져 Vercel 이 ISR Write 를 한다(옛 페이지 주석의 규칙). 날짜 문자열까지만 서버가 만들고
// 남은 날 계산과 자격 판정은 여기서 한다.
"use client";

import { useEffect, useState } from "react";
import { NoticeRail, type QualLine } from "./NoticeRail";
import type { BidNotice } from "@/lib/notice";

export function NoticeRailClient({ n }: { n: BidNotice }) {
  // 서버·첫 렌더에서는 공고 날짜 기준으로만 그린다 — 하이드레이션이 어긋나지 않게 오늘은 뒤에 넣는다.
  const [today, setToday] = useState<Date>(() => new Date(`${(n.bid_clse_date ?? "2000-01-01").slice(0, 10)}T00:00:00+09:00`));
  useEffect(() => {
    queueMicrotask(() => setToday(new Date()));
  }, []);

  // 자격은 '제한 있음/없음'까지만 말한다. 회사를 모르면 충족 여부를 판정하지 않는다 —
  // 이 화면은 로그인 없이도 열리고, 공고 쪽 필드만으로는 "누가" 되는지 알 수 없다.
  const quals: QualLine[] = [
    {
      label: "면허",
      state: n.indstryty_lmt_yn === "Y" ? "warn" : "none",
      text: n.indstryty_lmt_yn === "Y" ? (n.bidprc_psbl_indstryty_nm || "업종 제한 있음") : "제한 없음",
    },
    {
      label: "지역",
      state: n.rgn_lmt_yn === "Y" ? "warn" : "none",
      text: n.rgn_lmt_yn === "Y" ? (n.prtcpt_psbl_rgn_nm || "지역 제한 있음") : "제한 없음",
    },
    {
      label: "등록",
      state: n.bid_qlfct_rgst_dt ? "warn" : "none",
      text: n.bid_qlfct_rgst_dt
        ? `참가자격 등록 마감 ${new Date(n.bid_qlfct_rgst_dt).toLocaleString("ko-KR", {
            timeZone: "Asia/Seoul",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })}`
        : "별도 마감 없음",
    },
  ];

  return <NoticeRail n={n} quals={quals} today={today} />;
}
