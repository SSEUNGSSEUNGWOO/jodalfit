import { Brand } from "./Brand";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-bg-alt/40">
      <div className="mx-auto grid max-w-[1180px] gap-8 px-6 py-12 sm:grid-cols-[1.4fr_1fr_1fr] sm:px-8 sm:py-14">
        <div>
          <Brand size="md" />
          <p className="mt-3 max-w-md text-[13.5px] leading-relaxed text-ink-muted">
            jodalfit은 나라장터(국가종합전자조달) 공공데이터를 기반으로 입찰공고를 추천합니다.
            낙찰 결과를 보장하지 않으며, 의사결정의 보조 도구입니다.
          </p>
          <p className="mt-3 text-[12px] text-ink-soft tabular">
            데이터 출처: 조달청 나라장터 공공데이터 개방표준 · 매일 갱신
          </p>
        </div>
        <div>
          <span className="eyebrow text-ink">서비스</span>
          <ul className="mt-3 space-y-2 text-[13.5px] text-ink-muted">
            <li>
              <a href="/#how" className="hover:text-ink transition-colors">
                추천 방식
              </a>
            </li>
            <li>
              <a href="/#trust" className="hover:text-ink transition-colors">
                데이터 출처
              </a>
            </li>
            <li>
              <a href="mailto:hello@jodalfit.co.kr" className="hover:text-ink transition-colors">
                문의
              </a>
            </li>
          </ul>
        </div>
        <div>
          <span className="eyebrow text-ink">제공처</span>
          <ul className="mt-3 space-y-2 text-[13.5px] text-ink-muted">
            <li>국가종합전자조달 나라장터 (g2b.go.kr)</li>
            <li>공공데이터포털 (data.go.kr)</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-2 px-6 py-4 text-[12px] text-ink-soft sm:px-8">
          <span>© {new Date().getFullYear()} jodalfit</span>
          <span className="tabular">
            마지막 데이터 업데이트:{" "}
            {new Date().toLocaleDateString("ko-KR", {
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
