"use client";

import { useSyncExternalStore } from "react";

/** 브라우저에 마운트된 뒤에만 오늘(자정 기준)을 돌려준다. 서버 렌더와 하이드레이션 중에는 null.
 *
 *  날짜 의존 표시(D-day·골든타임·"진행 중")를 ISR 캐시 HTML에 굽지 않기 위한 장치다. 서버가 구운
 *  HTML에 오늘 날짜가 들어가면 데이터가 그대로인 공고도 매일 "다른 출력"이 되어 Vercel ISR Write
 *  (8KB 단위 과금)가 공고 1만 건 × 매일 발생했다 (2026-09 청구서 ISR Writes $40/월의 주원인). */
const subscribe = () => () => {};
let cached: Date | null = null;

function getClientToday(): Date {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  // useSyncExternalStore는 스냅샷 참조가 바뀌면 다시 렌더하므로 같은 날이면 같은 객체를 돌려준다.
  if (!cached || cached.getTime() !== now.getTime()) cached = now;
  return cached;
}

export function useToday(): Date | null {
  return useSyncExternalStore(subscribe, getClientToday, () => null);
}
