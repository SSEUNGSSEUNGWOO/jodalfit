// frontend/src/components/company/OwnCompanyBridge.tsx
// 회사 페이지의 다리 — 경쟁사 조회로 들어온 사람을 자기 회사 검색으로. 회사 페이지 방문자 3,390명 중 92%가 그 페이지만 보고
// 나갔고 추천 결과로 간 사람은 95명이었다(2026-10-26 PostHog). 네이버 유입의 중심이 회사 페이지라 여기가 입구다.
// 검색창은 입구와 같은 부품이되 회사 모드로 고정(탭 없음) — "우리 회사 기준으로 보기" 아래 "회사로 찾기" 탭은 같은 말이 두 번이었다(승우님 2026-10-27).
import { SearchSuggest } from "@/components/entry/SearchSuggest";

export function OwnCompanyBridge({ corpNm }: { corpNm: string }) {
  return (
    <div data-bridge className="mt-5 rounded-[6px] border border-hair bg-panel px-6 py-5 max-sm:px-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="m-0 text-[15px] font-[650] text-ink">우리 회사 기준으로 보기</h2>
        <span className="text-[12.5px] text-ink-g">이 페이지는 {corpNm} 기준입니다</span>
      </div>
      <p className="m-0 mt-2 max-w-[720px] text-[13.5px] leading-[1.7] text-ink-g">
        우리 회사 이름이나 사업자번호를 적으면 같은 방법으로 우리 회사가 지금 검토할 공고를 추립니다. 등록업종·공급물품·수주 이력이 기준입니다.
      </p>
      <div className="mt-3 max-w-[560px]"><SearchSuggest lock="company" placeholder="우리 회사 이름 또는 사업자등록번호" compact /></div>
    </div>
  );
}
