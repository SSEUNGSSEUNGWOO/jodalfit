import { BidCard } from "@/components/BidCard";
import { EmailCaptureForm } from "@/components/EmailCaptureForm";
import { FeatureCard } from "@/components/FeatureCard";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SearchForm } from "@/components/SearchForm";
import { StatCard } from "@/components/StatCard";
import { MOCK_BIDS } from "@/lib/mock-data";

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="flex-1">
        <Hero />
        <TrustStrip />
        <HowItWorks />
        <ResultPreview />
        <EmailCapture />
      </main>
      <Footer />
    </>
  );
}

function Hero() {
  return (
    <section className="relative">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 pt-16 sm:pt-24 pb-16 sm:pb-20">
        <div className="text-center max-w-[760px] mx-auto rise">
          <span className="inline-flex items-center gap-1.5 rounded-pill bg-brand-soft px-3 py-1.5 text-[12.5px] font-bold text-brand-strong">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand" />
            공공조달 입찰 추천
          </span>

          <h1 className="mt-6 text-[40px] sm:text-[60px] font-extrabold leading-[1.15] tracking-[-0.02em] text-ink">
            우리 회사가 따낼 만한
            <br />
            공공입찰만 모았어요.
          </h1>

          <p className="mt-6 text-[17px] sm:text-[19px] leading-[1.65] text-ink-3 max-w-[560px] mx-auto">
            회사명만 입력하면 과거 낙찰 이력을 분석해서<br className="hidden sm:inline" />
            가장 잘 맞는 공고 <span className="text-brand font-bold">TOP 5</span>를 추천해드려요.
          </p>
        </div>

        {/* Search */}
        <div className="mt-10 sm:mt-12 max-w-[640px] mx-auto rise [animation-delay:120ms]">
          <SearchForm autoFocus />
        </div>

        {/* Quick chips */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-1.5 rise [animation-delay:240ms]">
          <span className="text-[13px] text-ink-5 mr-1">예시</span>
          {["삼성SDS", "LG CNS", "메가존클라우드", "비트컴퓨터"].map((q) => (
            <a
              key={q}
              href={`/recommendations?company=${encodeURIComponent(q)}`}
              className="chip hover:bg-bg-soft-2 transition-colors"
            >
              {q}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function TrustStrip() {
  return (
    <section id="trust" className="border-y border-line bg-bg-soft">
      <div className="mx-auto max-w-[1140px] grid grid-cols-2 lg:grid-cols-4 gap-y-8 px-5 sm:px-8 py-10 sm:py-12">
        <StatCard
          label="입찰공고 분석"
          value="10,990"
          suffix="건"
          hint="최근 1주 신규"
        />
        <StatCard
          label="등록 회사"
          value="34,517"
          suffix="개"
          hint="누적 사업자번호"
        />
        <StatCard
          label="추천 가능"
          value="2,300+"
          hint="수주 이력 보유"
        />
        <StatCard
          label="갱신 주기"
          value="매일"
          hint="나라장터 OpenAPI"
        />
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-[1140px] px-5 sm:px-8 py-20 sm:py-28">
      <div className="text-center max-w-[640px] mx-auto">
        <span className="text-[13px] font-bold text-brand">왜 jodalfit인가요?</span>
        <h2 className="mt-3 text-[28px] sm:text-[36px] font-extrabold tracking-tight text-ink">
          키워드 알림으로 놓친 공고,<br />
          의미로 찾아드려요.
        </h2>
      </div>

      <div className="mt-12 sm:mt-14 grid gap-4 sm:grid-cols-3">
        <FeatureCard
          emoji="🎯"
          title="과거 낙찰 이력으로 매칭"
          body="키워드가 달라도 같은 영역이면 잡아내요. 회사가 실제로 따낸 공고들을 임베딩으로 비교합니다."
        />
        <FeatureCard
          emoji="🛡️"
          title="자격 안 맞는 공고는 제외"
          body="참가 가능 업종, 지역 제한, 마감 임박도, 추정가 적합도까지 먼저 거릅니다."
        />
        <FeatureCard
          emoji="💬"
          title="왜 추천했는지 알려드려요"
          body="추천 점수만 보여주지 않아요. 어떤 과거 수주와 닮았는지 자연어로 설명해드립니다."
        />
      </div>
    </section>
  );
}

function ResultPreview() {
  const sample = MOCK_BIDS[0];
  return (
    <section id="preview" className="border-y border-line bg-bg-soft">
      <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-20 sm:py-28">
        <div className="text-center max-w-[640px] mx-auto">
          <span className="text-[13px] font-bold text-brand">실제 추천 결과</span>
          <h2 className="mt-3 text-[28px] sm:text-[36px] font-extrabold tracking-tight text-ink">
            이런 식으로 추천해드려요.
          </h2>
          <p className="mt-4 text-[15.5px] leading-[1.65] text-ink-3">
            한 카드 안에서 <span className="font-bold text-ink">얼마나 맞나 · 왜 맞나 · 지금 액션할 가치</span>가
            한눈에 들어와요.
          </p>
        </div>

        <div className="mt-10 max-w-[820px] mx-auto">
          <BidCard bid={sample} rank={1} preview />
        </div>

        <p className="mt-6 text-center text-[12.5px] text-ink-5">
          ※ 샘플 데이터입니다. 실제 추천 결과가 아니에요.
        </p>
      </div>
    </section>
  );
}

function EmailCapture() {
  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-20 sm:py-24">
      <EmailCaptureForm />
    </section>
  );
}
