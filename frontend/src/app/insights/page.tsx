import type { Metadata } from "next";
import Link from "next/link";

import { Header } from "@/components/Header";
import { listAllInsights } from "@/lib/insights";

export const metadata: Metadata = {
  title: "주간 인사이트 — jodalfit",
  description:
    "공공조달 주간 인사이트 모음. 이번 주 검토할 만한 공고 TOP 10 (픽)과 시장 동향 리포트를 매주 발행합니다.",
  alternates: { canonical: "/insights" },
};

export default async function InsightsIndex() {
  const items = await listAllInsights();

  const picks = items.filter((i) => i.type === "picks");
  const market = items.filter((i) => i.type === "market");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1140px] px-5 sm:px-8 py-12">
        <header className="mb-12">
          <div className="text-[13px] font-semibold uppercase tracking-wider text-primary mb-2">
            매주 월요일 발행
          </div>
          <h1 className="text-[40px] font-bold tracking-tight text-foreground leading-tight">
            주간 인사이트
          </h1>
          <p className="mt-3 text-[17px] text-muted-foreground max-w-[560px] leading-relaxed">
            나라장터 8개 OpenAPI에서 매일 자동 수집한 데이터를 두 가지로 정리해
            발행합니다. 이번 주 검토할 만한 공고를 고른 <strong className="text-foreground">픽</strong>과
            시장 전반을 분석한 <strong className="text-foreground">동향</strong>.
          </p>
        </header>

        <section className="mb-14">
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="text-[22px] font-bold text-foreground">
              이번 주 픽
              <span className="ml-3 text-[14px] font-medium text-muted-foreground">
                검토할 만한 공고 TOP 10
              </span>
            </h2>
            <span className="text-[14px] text-muted-foreground">{picks.length}개 발행</span>
          </div>
          {picks.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center text-muted-foreground text-[14px]">
              아직 발행된 픽이 없습니다.
            </div>
          ) : (
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {picks.map((i) => (
                <li key={`${i.type}-${i.slug}`}>
                  <Link
                    href={`/insights/${i.type}/${i.slug}`}
                    className="block rounded-lg border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all"
                  >
                    <div className="text-[12px] font-semibold uppercase tracking-wider text-primary mb-1">
                      {i.slug}
                    </div>
                    <div className="text-[16px] font-bold text-foreground leading-snug">
                      {i.title}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                      {i.summary}
                    </div>
                    {i.evaluation_score && (
                      <div className="mt-3 text-[11px] text-muted-foreground">
                        품질 {i.evaluation_score.toFixed(2)}/5
                      </div>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="text-[22px] font-bold text-foreground">
              시장 동향
              <span className="ml-3 text-[14px] font-medium text-muted-foreground">
                데이터 리포트
              </span>
            </h2>
            <span className="text-[14px] text-muted-foreground">{market.length}개 발행</span>
          </div>
          {market.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center text-muted-foreground text-[14px]">
              아직 발행된 동향이 없습니다.
            </div>
          ) : (
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {market.map((i) => (
                <li key={`${i.type}-${i.slug}`}>
                  <Link
                    href={`/insights/${i.type}/${i.slug}`}
                    className="block rounded-lg border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all"
                  >
                    <div className="text-[12px] font-semibold uppercase tracking-wider text-primary mb-1">
                      {i.slug}
                    </div>
                    <div className="text-[16px] font-bold text-foreground leading-snug">
                      {i.title}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                      {i.summary}
                    </div>
                    {i.evaluation_score && (
                      <div className="mt-3 text-[11px] text-muted-foreground">
                        품질 {i.evaluation_score.toFixed(2)}/5
                      </div>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
