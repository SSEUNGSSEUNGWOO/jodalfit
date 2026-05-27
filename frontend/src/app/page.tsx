import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { BackgroundC } from "@/components/hero-bg/BackgroundC";
import { fetchActiveNoticesRoughCount } from "@/lib/notice";

export const revalidate = 3600;

export default async function HomePage() {
  const activeCount = await fetchActiveNoticesRoughCount().catch(() => 0);

  return (
    <>
      <Header />
      {/* Hero가 헤더(64px)를 뺀 뷰포트 전체를 차지 — 푸터는 스크롤해야 보이게.
          pb-72(=288px) 으로 컨베이어 영역 확보, BackgroundC가 absolute 배경. */}
      <main className="relative overflow-hidden flex flex-col justify-center min-h-[calc(100vh-4rem)] pb-72">
        <BackgroundC />
        <div className="relative z-10">
          <Hero activeCount={activeCount} />
        </div>
      </main>
      <Footer />
    </>
  );
}

function Hero({ activeCount }: { activeCount: number }) {
  return (
    <section className="w-full">
      <div className="mx-auto max-w-[880px] px-5 sm:px-8 py-12 sm:py-16">
        <div className="text-center max-w-[880px] mx-auto rise">
          <span className="inline-flex items-center gap-1.5 rounded-pill bg-primary/10 px-3 py-1.5 text-[12.5px] font-bold text-primary">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
            나라장터 입찰 디스커버리
          </span>

          <h1 className="mt-6 text-[36px] sm:text-[52px] font-extrabold leading-[1.15] tracking-[-0.02em] text-foreground break-keep">
            회사에 맞는 <span className="text-primary">나라장터</span> 공고를 검토 우선순위로 정리합니다.
          </h1>

          <p className="mt-6 text-[17px] sm:text-[19px] leading-[1.65] text-muted-foreground max-w-[640px] mx-auto break-keep">
            <span className="text-foreground font-semibold">회사명·사업자번호</span> 또는 관심 <span className="text-foreground font-semibold">키워드</span>를 입력합니다.
            등록업종·공급물품·수주 이력을 바탕으로 검토할 만한 나라장터 공고 <span className="text-primary font-bold">5건</span>을 정리합니다.
          </p>
        </div>

        {/* Search — 탭 + 모드별 예시 칩 통합 */}
        <div className="mt-10 sm:mt-12 max-w-[640px] mx-auto rise [animation-delay:120ms]">
          <SearchForm
            autoFocus
            examples={{
              company: ["삼성SDS", "LG CNS", "메가존클라우드", "비트컴퓨터"],
              keywords: ["교육 IT 유지보수", "도로 정비공사", "의약품 단가계약", "조경 유지관리"],
            }}
          />
        </div>

        {/* 신뢰 한 줄 */}
        <p className="mt-10 text-center text-[13px] text-muted-foreground rise [animation-delay:360ms]">
          <span className="font-bold text-foreground">나라장터(G2B)</span>
          {" "}진행 중 공고{" "}
          <span className="font-bold text-foreground tabular-nums">
            {activeCount > 0 ? activeCount.toLocaleString("ko-KR") : "—"}건
          </span>
          {" "}· 매일 자동 갱신 · 공공 OpenAPI 기반
        </p>
      </div>
    </section>
  );
}
