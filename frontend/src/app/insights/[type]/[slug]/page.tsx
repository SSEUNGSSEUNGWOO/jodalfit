import type { Metadata } from "next";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Header } from "@/components/Header";
import { DonutChart, HorizontalBarChart } from "@/components/InsightCharts";
import { fetchInsight, listInsightsByType, type InsightType } from "@/lib/insights";

type Params = Promise<{ type: string; slug: string }>;

function isType(t: string): t is InsightType {
  return t === "picks" || t === "market" || t === "guide";
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { type, slug } = await params;
  if (!isType(type)) return {};
  const insight = await fetchInsight(type, slug);
  if (!insight) return {};
  return {
    title: `${insight.meta.title} — 조달핏`,
    description: insight.meta.summary,
    alternates: { canonical: `/insights/${type}/${slug}` },
    openGraph: {
      title: insight.meta.title,
      description: insight.meta.summary,
      type: "article",
      publishedTime: insight.meta.published_at,
    },
  };
}

export async function generateStaticParams() {
  const [picks, market, guide] = await Promise.all([
    listInsightsByType("picks"),
    listInsightsByType("market"),
    listInsightsByType("guide"),
  ]);
  return [...picks, ...market, ...guide].map((i) => ({ type: i.type, slug: i.slug }));
}

export default async function InsightPage({ params }: { params: Params }) {
  const { type, slug } = await params;
  if (!isType(type)) notFound();
  const insight = await fetchInsight(type, slug);
  if (!insight) notFound();

  const typeLabel =
    type === "picks" ? "이번 주 픽" : type === "market" ? "이번 주 동향" : "가이드";
  const heroSrc =
    insight.meta.cover_image && insight.meta.cover_image.trim()
      ? insight.meta.cover_image
      : `/insights/${type}/${insight.slug}/opengraph-image`;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[820px] px-5 sm:px-8 py-10">
        <div className="mb-3 flex items-center gap-2 text-[13px] font-semibold uppercase tracking-wider text-primary">
          <span className="inline-block size-1.5 rounded-full bg-primary" />
          {typeLabel}
          {insight.meta.week_start && insight.meta.week_end && (
            <> · {insight.meta.week_start} ~ {insight.meta.week_end}</>
          )}
        </div>

        {/* Hero — cover_image 우선, 없으면 자동 OG */}
        <div className="mb-6 rounded-xl overflow-hidden border border-border bg-muted aspect-[1200/630]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={heroSrc}
            alt={insight.meta.title}
            className="w-full h-full object-cover"
          />
        </div>

        {/* market 차트 — hero 직후, 본문 표 위에 시각 임팩트 */}
        {type === "market" && (insight.meta.chart_bsns || insight.meta.chart_price) && (
          <div className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            {insight.meta.chart_bsns && (
              <DonutChart title="업무구분 분포" data={insight.meta.chart_bsns} />
            )}
            {insight.meta.chart_price && (
              <HorizontalBarChart title="예산 규모 분포" data={insight.meta.chart_price} />
            )}
          </div>
        )}

        <article className="prose-jodalfit">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-[34px] font-bold tracking-tight text-foreground leading-tight mt-2 mb-6">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-[22px] font-bold text-foreground mt-10 mb-3">
                  {children}
                </h2>
              ),
              p: ({ children }) => (
                <p className="text-[16px] leading-[1.85] text-foreground my-4">{children}</p>
              ),
              ul: ({ children }) => (
                <ul className="space-y-1.5 my-4 text-[15px] text-foreground list-disc pl-5">
                  {children}
                </ul>
              ),
              li: ({ children }) => <li>{children}</li>,
              em: ({ children }) => (
                <em className="not-italic block text-[14px] font-medium text-muted-foreground bg-muted/60 border-l-2 border-primary pl-3 py-1.5 my-2 rounded-r">
                  {children}
                </em>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">{children}</strong>
              ),
              blockquote: ({ children }) => (
                <blockquote className="text-[16px] text-muted-foreground border-l-2 border-border pl-4 my-4">
                  {children}
                </blockquote>
              ),
              hr: () => <hr className="my-8 border-border" />,
              a: ({ href, children }) => (
                <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80">
                  {children}
                </a>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-5">
                  <table className="w-full text-[14px] border-collapse">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="border-b border-border">{children}</thead>,
              th: ({ children, style }) => (
                <th
                  className="px-3 py-2 text-left font-semibold text-foreground"
                  style={style as React.CSSProperties}
                >
                  {children}
                </th>
              ),
              td: ({ children, style }) => (
                <td
                  className="px-3 py-2 border-t border-border text-foreground"
                  style={style as React.CSSProperties}
                >
                  {children}
                </td>
              ),
            }}
          >
            {insight.body}
          </ReactMarkdown>
        </article>

        {/* 운영자 메모 — 개발 환경에서만 표시. cover_image 미채운 페이지에서 프롬프트 카피용. */}
        {process.env.NODE_ENV === "development" &&
          !insight.meta.cover_image?.trim() &&
          insight.meta.image_prompt && (
            <aside className="mt-10 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-5">
              <div className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-wider text-primary mb-2">
                <span className="inline-block size-1.5 rounded-full bg-primary" />
                운영자 메모 · 커버 이미지 프롬프트
              </div>
              <p className="text-[14px] text-foreground leading-relaxed whitespace-pre-line">
                {insight.meta.image_prompt}
              </p>
              <p className="mt-3 text-[12px] text-muted-foreground leading-relaxed">
                위 프롬프트로 외부 도구(클로드 디자인, DALL-E, Imagen 등)에서 이미지를 만들고
                <code className="mx-1 px-1.5 py-0.5 rounded bg-muted text-[11px]">
                  frontmatter cover_image: /...
                </code>
                에 경로를 적어주세요. 비어 있을 동안에는 자동 OG가 hero로 사용됩니다.
              </p>
            </aside>
          )}

        <footer className="mt-10 pt-6 border-t border-border flex justify-between items-center text-[13px] text-muted-foreground">
          <div>발행 {new Date(insight.meta.published_at).toLocaleDateString("ko-KR")}</div>
          <a href="/insights" className="text-primary font-semibold hover:opacity-80">
            ← 다른 주차 인사이트
          </a>
        </footer>
      </main>
    </>
  );
}
