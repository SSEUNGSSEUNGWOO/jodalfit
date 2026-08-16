import type { Metadata } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "조달핏이란 — 나라장터 입찰 디스커버리",
  description:
    "jodalfit은 회사 등록업종·공급물품·수주 이력을 분석해 나라장터 공공입찰 중 검토할 만한 공고를 골라주는 디스커버리 도구입니다. 알고리즘 동작 방식과 데이터 출처를 안내합니다.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <Hero />
        <What />
        <How />
        <Different />
        <DataSources />
        <Limits />
        <Contact />
      </main>
      <Footer />
    </>
  );
}

function Section({
  eyebrow,
  title,
  children,
  bg,
}: {
  eyebrow?: string;
  title: string;
  children: React.ReactNode;
  bg?: "muted";
}) {
  return (
    <section className={bg === "muted" ? "border-y border-border bg-muted/30" : ""}>
      <div className="mx-auto max-w-[820px] px-5 sm:px-8 py-12 sm:py-16">
        {eyebrow && (
          <div className="mb-2 text-[12.5px] font-bold uppercase tracking-wider text-primary">
            {eyebrow}
          </div>
        )}
        <h2 className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
          {title}
        </h2>
        <div className="mt-5 space-y-4 text-[15.5px] leading-[1.8] text-foreground/85 break-keep">
          {children}
        </div>
      </div>
    </section>
  );
}

function Hero() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-[820px] px-5 sm:px-8 py-16 sm:py-24">
        <h1 className="font-gc-serif font-black text-[34px] sm:text-[48px] leading-[1.25] tracking-[-0.02em] text-gc-ink break-keep">
          나라장터 공고를 회사 기준으로 정리하는 디스커버리 도구
        </h1>
        <p className="mt-6 text-[17px] leading-[1.7] text-muted-foreground break-keep">
          jodalfit은 회사 등록업종·공급물품·과거 수주 이력을 분석해 나라장터 공공입찰 중 검토할 만한 공고를 정리합니다.
          키워드 알림만으로 찾기 어려운 공고와 자격이 맞지 않는 공고를 줄이고, 검토 시간을 줄이는 데 초점을 둡니다.
        </p>
      </div>
    </section>
  );
}

function What() {
  return (
    <Section eyebrow="What" title="무엇을 합니다">
      <p>
        회사명·사업자번호를 입력하면 회사 기준으로 검토할 만한 나라장터 공고 5건을 추천합니다.
        키워드(예: "교육 IT 유지보수")로 관심 영역을 탐색할 수도 있습니다.
        각 추천에는 매칭 점수와 함께 <strong className="text-foreground">추천 이유</strong>가 한 줄로 표시됩니다.
      </p>
      <p>
        낙찰을 보장하는 서비스가 아니라 <strong className="text-foreground">검토 우선순위를 정리하는 도구</strong>입니다.
        나라장터 진행 공고 중 사람이 직접 훑기 어려운 범위를 알고리즘으로 좁혀,
        판단에 필요한 후보를 먼저 보여줍니다.
      </p>
    </Section>
  );
}

function How() {
  return (
    <Section eyebrow="How" title="어떻게 동작합니다" bg="muted">
      <ol className="space-y-3 list-decimal pl-5">
        <li>
          <strong className="text-foreground">회사 영역을 이해합니다.</strong>
          {" "}등록업종·공급물품·과거 수주 이력을 종합해 주요 사업 영역을 파악합니다.
        </li>
        <li>
          <strong className="text-foreground">의미가 가까운 공고를 모읍니다.</strong>
          {" "}진행 중 공고 중 회사 영역과 의미적으로 가까운 후보를 우선 추립니다. 같은 단어가 없어도 의미가 가까운 공고를 후보로 모읍니다.
        </li>
        <li>
          <strong className="text-foreground">검토 가치를 평가합니다.</strong>
          {" "}마감 시점·참가 자격·사업 규모·과거 거래 관계를 함께 보고 점수를 조정합니다. 자격 조건이 맞지 않는 공고는 우선순위를 낮춥니다.
        </li>
        <li>
          <strong className="text-foreground">추천 이유를 한 줄로 설명합니다.</strong>
          {" "}점수만 보여주지 않고 어떤 부분이 맞물려 추천됐는지 자연어로 안내합니다.
        </li>
      </ol>
      <p className="text-[14px] text-muted-foreground">
        키워드 검색 모드는 회사 정보 없이 입력한 영역과 의미가 가까운 공고를 찾습니다.
        영업 탐색이나 시장 조사에 적합합니다.
      </p>
    </Section>
  );
}

function Different() {
  return (
    <Section eyebrow="Why" title="키워드 알림과 다른 점">
      <ul className="space-y-3 list-disc pl-5">
        <li>
          <strong className="text-foreground">단어 매칭이 아니라 의미 매칭입니다.</strong> 같은 단어가 없어도 의미가 가까운 공고를 찾습니다.
        </li>
        <li>
          <strong className="text-foreground">회사 영역 기준으로 봅니다.</strong> 단순 업종 코드가 아니라 등록업종·공급물품·과거 수주를 종합해 실제 사업 영역을 파악합니다.
        </li>
        <li>
          <strong className="text-foreground">자격 조건을 함께 봅니다.</strong> 참가 자격이 맞지 않는 공고는 우선순위를 낮춥니다.
        </li>
        <li>
          <strong className="text-foreground">추천 이유를 안내합니다.</strong> 점수만 보여주지 않고 어떤 근거로 추천됐는지 한 줄로 설명합니다.
        </li>
      </ul>
    </Section>
  );
}

function DataSources() {
  return (
    <Section eyebrow="Data" title="데이터 출처" bg="muted">
      <p>
        조달청 <strong className="text-foreground">나라장터(국가종합전자조달, G2B)</strong>가
        {" "}<a
          href="https://www.data.go.kr"
          target="_blank"
          rel="noreferrer"
          className="text-primary underline underline-offset-2 hover:opacity-80"
        >
          공공데이터포털
        </a>로 공개하는 공식 OpenAPI를 활용합니다. 입찰공고·계약·회사 정보·자격 제한 등 추천에 필요한 데이터를 매일 새벽 자동으로 갱신합니다.
      </p>
      <p className="text-[14px] text-muted-foreground">
        데이터는 공공데이터포털 라이선스를 따르며, jodalfit은 공개 데이터를 추천 목적에 맞게 정리하고 재배열합니다.
      </p>
    </Section>
  );
}

function Limits() {
  return (
    <Section eyebrow="Limits" title="할 수 없는 것, 보장하지 않는 것">
      <ul className="space-y-3 list-disc pl-5">
        <li>
          <strong className="text-foreground">낙찰을 보장하지 않습니다.</strong> 매칭 점수는 "검토할 가치"의 신호이지 "이길 가능성"이 아닙니다.
        </li>
        <li>
          <strong className="text-foreground">자격 검증은 보조 신호입니다.</strong> 최종 입찰 가능 여부는 공고 원문과 회사 자격으로 직접 확인해야 합니다.
        </li>
        <li>
          <strong className="text-foreground">회사 데이터가 부족하면 키워드 검색으로 전환합니다.</strong> 등록업종·공급물품 정보가 적재되지 않은 회사는 추천 정확도가 낮을 수 있습니다.
        </li>
        <li>
          <strong className="text-foreground">의사결정의 보조 도구</strong>로 사용해야 합니다. 최종 판단은 사람이 합니다.
        </li>
      </ul>
    </Section>
  );
}

function Contact() {
  return (
    <Section eyebrow="Contact" title="연락처" bg="muted">
      <p>
        문의·제안·버그 리포트: {" "}
        <a
          href="mailto:jsw7980@gmail.com"
          className="text-primary font-semibold underline underline-offset-2 hover:opacity-80"
        >
          jsw7980@gmail.com
        </a>
      </p>
      <p className="text-[14px] text-muted-foreground">
        © {new Date().getFullYear()} jodalfit. 데이터는 공공데이터포털 라이선스를 따릅니다.
      </p>
    </Section>
  );
}
