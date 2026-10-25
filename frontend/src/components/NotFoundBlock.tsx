// frontend/src/components/NotFoundBlock.tsx
// 404 본문 — 루트(app/not-found.tsx, 없는 주소)와 (renewal)/not-found.tsx(notFound() — 회사·공고 없음)가 같이 쓴다.
import { Btn } from "@/components/Btn";
import { Panel } from "@/components/Panel";

export function NotFoundBlock() {
  return (
    <div className="mx-auto mt-12 max-w-[520px] max-sm:mt-5">
      <h1 className="m-0 mb-3 text-[28px] font-semibold tracking-[-0.03em] text-ink max-sm:text-[22px]">페이지가 없습니다</h1>
      <Panel className="px-7 pb-7 pt-[26px] max-sm:px-4 max-sm:pb-[22px] max-sm:pt-5">
        <p className="m-0 text-[14.5px] leading-[1.75] text-ink-body break-keep">
          주소가 바뀌었거나 삭제된 페이지입니다. 회사 또는 공고를 찾으려면 입구에서 검색합니다.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Btn variant="dark" href="/">회사로 찾기</Btn>
          <Btn href="/notices">입찰공고 둘러보기</Btn>
        </div>
      </Panel>
    </div>
  );
}
