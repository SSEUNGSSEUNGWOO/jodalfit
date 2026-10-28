// frontend/src/components/Gate.tsx
import { Btn } from "@/components/Btn";

/** 표 안 게이트 — 공개 5건 뒤, 보관·전체 확인의 이점과 인증 후 복귀 경로. */
export function Gate({ rest, next }: { rest: number; next: string }) {
  const q = `?next=${encodeURIComponent(next)}`;
  return (
    <div data-gate className="hairline flex flex-wrap items-center gap-x-4 gap-y-3 py-5 text-[14px]">
      <div className="min-w-0 flex-1 basis-[280px]">
        <b className="font-semibold text-ink">나머지 {rest}건은 로그인 후 공개</b>
        <span className="mt-1 block text-[13px] leading-[1.6] text-ink-dim">무료 가입으로 전체 공고를 확인하고, 검토할 공고를 보관합니다.</span>
      </div>
      <span className="flex gap-1.5 max-sm:w-full">
        <Btn href={`/login${q}`} variant="line">로그인</Btn>
        <Btn href={`/signup${q}`} variant="dark">무료 가입</Btn>
      </span>
    </div>
  );
}
