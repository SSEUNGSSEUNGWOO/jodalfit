// frontend/src/components/notice/NoticeBridge.tsx
// 공고 페이지의 다리 — 공고 하나를 보러 온 사람을 자기 회사 검색으로. 공고 페이지로 들어온 5,455명 중 추천 결과를 본 사람은 13명,
// 로그인 화면까지 간 사람은 1명이었다(2026-11-12 PostHog 14일). 유입의 절반이 이 화면인데 다음 걸음이 nav 밖에 없었다.
// 회사 페이지의 다리(OwnCompanyBridge)와 같은 부품·같은 고정(회사 모드, 탭 없음). 공고 본문을 밀어내지 않게 한 줄 높이로 둔다.
// 서버 출력에 '오늘'을 넣지 않는다(page.tsx 머리 주석) — 마감 여부에 따라 문구를 가르지 않는다.
import { SearchSuggest } from "@/components/entry/SearchSuggest";

export function NoticeBridge() {
  return (
    <div data-bridge className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-3 rounded-[6px] border border-hair bg-panel px-6 py-4 max-sm:px-4">
      <div className="min-w-0 flex-1 basis-[320px]">
        <h2 className="m-0 text-[15px] font-[650] text-ink">우리 회사가 검토할 공고 보기</h2>
        <p className="m-0 mt-1 text-[13px] leading-[1.6] text-ink-g">
          회사 이름이나 사업자번호를 적으면 등록업종·공급물품·수주 이력을 기준으로 지금 검토할 공고를 추립니다.
        </p>
      </div>
      <div className="min-w-0 max-w-[460px] flex-1 basis-[320px]"><SearchSuggest lock="company" placeholder="우리 회사 이름 또는 사업자등록번호" compact /></div>
    </div>
  );
}
