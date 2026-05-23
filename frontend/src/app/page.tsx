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
    <section className="relative overflow-hidden">
      {/* Subtle grid pattern background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(18,53,91,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(18,53,91,0.06) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          maskImage:
            "linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.15) 60%, transparent 100%)",
        }}
      />
      <div className="relative mx-auto max-w-[1180px] px-6 pt-14 pb-16 sm:px-8 sm:pt-20 sm:pb-24">
        <div className="grid items-start gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <div className="rise">
            <div className="flex items-center gap-2.5">
              <span className="inline-flex items-center gap-1 rounded-pill border border-teal-300 bg-teal-50 px-2.5 py-1 text-[11px] font-semibold tracking-[0.14em] uppercase text-teal-700">
                <span className="inline-block h-1 w-1 rounded-full bg-teal-500" />
                공공조달 매칭
              </span>
              <span className="hidden text-[12px] tabular text-ink-soft sm:inline">
                Public Procurement Recommender
              </span>
            </div>

            <h1 className="mt-7 text-[40px] font-bold leading-[1.15] tracking-[-0.025em] text-ink-strong sm:text-[52px] sm:leading-[1.1]">
              우리 회사가 따낼 만한
              <br />
              <span className="text-navy">공공입찰</span>,<br />
              <span className="relative inline-block">
                30초
                <span
                  aria-hidden
                  className="absolute -bottom-1 left-0 h-[6px] w-full bg-teal-300/40 -z-0"
                />
              </span>
              <span className="relative z-10"> 만에 확인하세요.</span>
            </h1>

            <p className="mt-7 max-w-[480px] text-[16px] leading-[1.7] text-ink-muted sm:text-[17px]">
              키워드 검색이 아닙니다. <span className="text-ink font-medium">과거 낙찰 이력</span>과
              현재 공고를 의미 단위로 비교해, 우리 회사가 가장 잘 맞는 공고
              <span className="text-ink font-medium"> TOP 5</span>를 추천합니다.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-ink-muted">
              <span className="flex items-center gap-1.5">
                <Dot tone="teal" /> 회원가입 불필요
              </span>
              <span className="flex items-center gap-1.5">
                <Dot tone="navy" /> 나라장터 공식 데이터
              </span>
              <span className="flex items-center gap-1.5">
                <Dot tone="muted" /> 매일 자동 갱신
              </span>
            </div>
          </div>

          {/* Search panel */}
          <div className="rise [animation-delay:120ms] lg:pt-2">
            <div className="rounded-card border border-line bg-surface p-6 shadow-[0_24px_48px_-32px_rgba(18,53,91,0.18)] sm:p-7">
              <div className="flex items-center justify-between">
                <span className="eyebrow text-teal-700">회사명 입력</span>
                <span className="text-[11px] tabular text-ink-soft">STEP 1</span>
              </div>
              <SearchForm autoFocus className="mt-4" />

              <div className="mt-7 grid grid-cols-3 gap-3 border-t border-line pt-5">
                <ProcessStep n="1" label="회사 식별" />
                <ProcessStep n="2" label="과거 낙찰 분석" />
                <ProcessStep n="3" label="공고 매칭" />
              </div>
            </div>

            <p className="mt-4 px-2 text-[12px] text-ink-soft">
              예시 검색어:{" "}
              <span className="font-medium text-ink-muted">
                삼성SDS · LG CNS · 메가존클라우드
              </span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function ProcessStep({ n, label }: { n: string; label: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] tabular text-teal-600">0{n}.</span>
      <span className="text-[12.5px] font-medium text-ink">{label}</span>
    </div>
  );
}

function Dot({ tone }: { tone: "teal" | "navy" | "muted" }) {
  const colors = {
    teal: "bg-teal-500",
    navy: "bg-navy",
    muted: "bg-ink-soft",
  };
  return (
    <span
      aria-hidden
      className={`inline-block h-1.5 w-1.5 rounded-full ${colors[tone]}`}
    />
  );
}

function TrustStrip() {
  return (
    <section id="trust" className="border-y border-line bg-surface">
      <div className="mx-auto grid max-w-[1180px] grid-cols-2 gap-y-7 px-6 py-8 sm:grid-cols-4 sm:px-8 sm:py-9">
        <StatCard
          label="입찰공고 분석"
          value="10,990"
          suffix="건"
          hint="최근 1주 신규"
        />
        <StatCard
          label="회사 마스터"
          value="34,517"
          suffix="개"
          hint="누적 사업자번호"
        />
        <StatCard
          label="추천 가능 회사"
          value="2,300"
          suffix="+"
          hint="수주 이력 보유"
        />
        <StatCard
          label="데이터 출처"
          value="나라장터"
          hint="조달청 공식 OpenAPI"
        />
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-[1180px] px-6 py-20 sm:px-8 sm:py-24">
      <div className="max-w-2xl">
        <div className="flex items-center gap-2">
          <span className="eyebrow text-teal-700">왜 다른가</span>
          <span className="h-px w-8 bg-teal-500" aria-hidden />
        </div>
        <h2 className="mt-4 text-[30px] font-bold tracking-tight text-ink-strong sm:text-[36px]">
          키워드 알림으로 놓친 공고,<br />
          jodalfit은 의미 단위로 찾아냅니다.
        </h2>
      </div>

      <div className="mt-12 grid gap-4 sm:grid-cols-3 sm:gap-5">
        <FeatureCard
          index="01."
          eyebrow="유사 수주 매칭"
          title="과거 낙찰 이력 기준 매칭"
          body="회사가 실제로 따낸 공고들을 임베딩으로 표현하고, 신규 공고와 의미적으로 비교합니다. 키워드가 달라도 같은 영역이면 잡아냅니다."
        />
        <FeatureCard
          index="02."
          eyebrow="자격 자동 검증"
          title="마감·금액·지역 조건 자동 반영"
          body="참가 가능 업종, 지역 제한, 마감 임박도, 추정가 적합도를 먼저 필터합니다. '비슷한데 못 들어가는' 공고를 추천에서 제외합니다."
        />
        <FeatureCard
          index="03."
          eyebrow="설명 가능한 매칭"
          title="왜 추천했는지 그 자리에서"
          body="추천 점수만이 아니라 '어떤 과거 수주와 닮았는지, 어떤 조건이 맞는지'를 자연어로 함께 보여줍니다. 의사결정의 근거가 됩니다."
        />
      </div>
    </section>
  );
}

function ResultPreview() {
  const sample = MOCK_BIDS[0];
  return (
    <section className="border-t border-line bg-bg-alt/40">
      <div className="mx-auto max-w-[1180px] px-6 py-20 sm:px-8 sm:py-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="eyebrow text-teal-700">결과 미리보기</span>
              <span className="h-px w-8 bg-teal-500" aria-hidden />
            </div>
            <h2 className="mt-3 text-[28px] font-bold tracking-tight text-ink-strong sm:text-[32px]">
              실제 추천 카드는 이렇게 보입니다.
            </h2>
            <p className="mt-2 text-[15px] text-ink-muted">
              한 카드 안에서 <span className="text-ink font-medium">얼마나 맞나 · 왜 맞나 · 지금 액션할 가치</span>가
              한눈에 드러납니다.
            </p>
          </div>
          <div className="hidden text-[12px] tabular text-ink-soft sm:block">
            샘플 데이터 · 실제 추천 결과 아님
          </div>
        </div>

        <div className="mt-10">
          <BidCard bid={sample} rank={1} preview />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Annotate index="A" title="매칭 점수">
            과거 낙찰 패턴과의 의미 유사도 + 자격/예산/마감 가산점이 합산된 적합도입니다.
          </Annotate>
          <Annotate index="B" title="추천 이유">
            기존 수주 이력의 어떤 부분과 닮았는지 LLM이 풀어 설명합니다. 점수의 근거.
          </Annotate>
          <Annotate index="C" title="근거 태그">
            과거 수주 패턴 · 마감 여유 · 예산 적합도 같은 매칭 신호를 키워드로 보여줍니다.
          </Annotate>
        </div>
      </div>
    </section>
  );
}

function Annotate({
  index,
  title,
  children,
}: {
  index: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-line pt-4">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[12px] font-bold tabular text-teal-600">
          {index}
        </span>
        <span className="text-[13.5px] font-semibold text-ink">{title}</span>
      </div>
      <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-muted">
        {children}
      </p>
    </div>
  );
}

function EmailCapture() {
  return (
    <section className="mx-auto max-w-[1180px] px-6 py-20 sm:px-8 sm:py-24">
      <EmailCaptureForm />
    </section>
  );
}
