// frontend/src/components/Gate.tsx
import { Btn } from "@/components/Btn";

/** 표 안 게이트 — 5건 뒤. "나머지 N건은 로그인 후 공개" + 로그인 / 회원가입. 끝나면 next 로 돌아온다. */
export function Gate({ rest, next }: { rest: number; next: string }) {
  const q = `?next=${encodeURIComponent(next)}`;
  return (
    <div className="hairline flex flex-wrap items-center gap-3.5 py-6 text-[14.5px]">
      <div>
        <b className="font-semibold text-ink">나머지 {rest}건은 로그인 후 공개</b>
        <span className="mt-1 block text-[13.5px] text-ink-dim">상위 5건은 로그인 없이 공개</span>
      </div>
      <span className="flex-1" />
      <span className="flex gap-1.5 max-sm:w-full">
        <Btn href={`/login${q}`} variant="line">로그인</Btn>
        <Btn href={`/signup${q}`} variant="dark">회원가입</Btn>
      </span>
    </div>
  );
}
