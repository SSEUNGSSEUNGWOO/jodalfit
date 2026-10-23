import Link from "next/link";

/** 바닥 — 출처·갱신(카피 원칙: 상시 명시), 약관·개인정보·비공개 요청, 문의. 공문 톤. */
export function SiteFooter({ updatedAt }: { updatedAt?: string }) {
  return (
    <footer className="mt-16 border-t border-hair pt-6 pb-10 text-[12.5px] text-ink-mute leading-[1.7]">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <span>나라장터(국가종합전자조달) 공공데이터 기반 · 매일 05:00 갱신{updatedAt ? ` · 기준일 ${updatedAt}` : ""}</span>
        <span className="flex flex-wrap gap-x-4 gap-y-1">
          <Link href="/terms" className="u-link text-ink">이용약관</Link>
          <Link href="/privacy" className="u-link text-ink">개인정보처리방침</Link>
          <Link href="/privacy#company-optout" className="u-link">기업 정보 비공개 요청</Link>
          <a href="mailto:jsw7980@gmail.com?subject=%EC%A1%B0%EB%8B%AC%ED%95%8F%20%EB%AC%B8%EC%9D%98" className="u-link">문의</a>
        </span>
      </div>
      <p className="mt-2">추천은 검토 순서이며 낙찰을 예측하지 않습니다. © {new Date().getFullYear()} 조달핏</p>
    </footer>
  );
}
