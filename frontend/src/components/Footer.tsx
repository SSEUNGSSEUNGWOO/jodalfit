import { Brand } from "./Brand";

export function Footer() {
  const today = new Date();
  return (
    <footer className="mt-24 bg-bg-soft border-t border-line">
      <div className="mx-auto grid max-w-[1140px] gap-10 px-5 py-12 sm:px-8 sm:py-14 sm:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Brand size="md" />
          <p className="mt-3 max-w-md text-[13.5px] leading-relaxed text-ink-4">
            jodalfit은 나라장터(국가종합전자조달) 공공데이터를 기반으로
            입찰공고를 추천합니다. 낙찰 결과를 보장하지 않으며 의사결정의 보조 도구입니다.
          </p>
          <p className="mt-3 text-[12.5px] text-ink-5">
            데이터 출처 · 공공데이터포털 OpenAPI · 매일 갱신
          </p>
          <p className="mt-3 text-[12.5px] text-ink-4">
            의견·문의 ·{" "}
            <a
              href="mailto:jsw7980@gmail.com?subject=jodalfit%20%EC%9D%98%EA%B2%AC"
              className="font-semibold text-ink hover:underline"
            >
              jsw7980@gmail.com
            </a>
          </p>
        </div>
        <div>
          <span className="text-[13px] font-bold text-ink">서비스</span>
          <ul className="mt-3 space-y-2 text-[13.5px] text-ink-3">
            <li>
              <a href="/notices" className="hover:text-ink transition-colors">
                공고 둘러보기
              </a>
            </li>
            <li>
              <a href="/insights" className="hover:text-ink transition-colors">
                주간 인사이트
              </a>
            </li>
            <li>
              <a
                href="mailto:jsw7980@gmail.com"
                className="hover:text-ink transition-colors"
              >
                문의
              </a>
            </li>
          </ul>
        </div>
        <div>
          <span className="text-[13px] font-bold text-ink">데이터</span>
          <ul className="mt-3 space-y-2 text-[13.5px] text-ink-3">
            <li>나라장터 (g2b.go.kr)</li>
            <li>공공데이터포털 (data.go.kr)</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-[1140px] flex-wrap items-center justify-between gap-2 px-5 py-4 text-[12px] text-ink-5 sm:px-8">
          <span>© {today.getFullYear()} jodalfit</span>
          <span className="tabular">
            업데이트 ·{" "}
            {today.toLocaleDateString("ko-KR", {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            })}
          </span>
        </div>
      </div>
    </footer>
  );
}
