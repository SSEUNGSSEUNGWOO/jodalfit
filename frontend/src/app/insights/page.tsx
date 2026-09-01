import type { Metadata } from "next";
import Link from "next/link";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { listAllInsights } from "@/lib/insights";

export const metadata: Metadata = {
  title: "주간 인사이트 — 조달핏",
  description:
    "이번 주에 검토할 만한 공고와 공공조달 시장 동향을 매주 정리해 드립니다.",
  alternates: { canonical: "/insights" },
};

function weekLabel(slug: string) {
  const m = slug.match(/^(\d{4})-w(\d+)/);
  return m ? `${m[1]} W${m[2]}` : null;
}

export default async function InsightsIndex() {
  const items = await listAllInsights();

  const picks = items.filter((i) => i.type === "picks");
  const market = items.filter((i) => i.type === "market");
  const guides = items.filter((i) => i.type === "guide");

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <div className="mx-auto max-w-[1140px] px-5 sm:px-8 py-12">
        <header className="mb-12">
          <h1 className="font-gc-serif font-black text-[34px] sm:text-[40px] tracking-[-0.02em] text-gc-ink leading-tight">
            주간 인사이트
          </h1>
          <p className="mt-3 text-[17px] text-muted-foreground max-w-[560px] leading-relaxed">
            나라장터 공개 데이터를 바탕으로 이번 주에 검토할 만한 공고와
            시장의 흐름을 매주 정리해 드려요.
          </p>
        </header>

        <section className="mb-14">
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="font-gc-serif font-black text-[22px] tracking-[-0.02em] text-gc-ink">
              이번 주 픽
              <span className="ml-3 text-[14px] font-medium text-muted-foreground">
                검토할 만한 공고 선별
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
                      {[weekLabel(i.slug), i.category].filter(Boolean).join(" · ") || i.slug}
                    </div>
                    <div className="text-[16px] font-bold text-foreground leading-snug">
                      {i.title}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                      {i.summary}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {guides.length > 0 && (
          <section className="mb-14">
            <div className="flex items-baseline justify-between mb-5">
              <h2 className="font-gc-serif font-black text-[22px] tracking-[-0.02em] text-gc-ink">
                공공조달 가이드
                <span className="ml-3 text-[14px] font-medium text-muted-foreground">
                  처음 시작하는 회사용
                </span>
              </h2>
              <span className="text-[14px] text-muted-foreground">{guides.length}개</span>
            </div>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {guides.map((i) => (
                <li key={`${i.type}-${i.slug}`}>
                  <Link
                    href={`/insights/${i.type}/${i.slug}`}
                    className="block rounded-lg border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all"
                  >
                    <div className="text-[12px] font-semibold uppercase tracking-wider text-primary mb-1">
                      가이드
                    </div>
                    <div className="text-[16px] font-bold text-foreground leading-snug">
                      {i.title}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                      {i.summary}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section>
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="font-gc-serif font-black text-[22px] tracking-[-0.02em] text-gc-ink">
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
                      {[weekLabel(i.slug), i.category].filter(Boolean).join(" · ") || i.slug}
                    </div>
                    <div className="text-[16px] font-bold text-foreground leading-snug">
                      {i.title}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                      {i.summary}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        </div>
      </main>
      <Footer className="mt-0" />
    </>
  );
}
