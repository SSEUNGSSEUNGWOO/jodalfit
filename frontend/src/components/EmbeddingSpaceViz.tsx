"use client";

import { useState } from "react";
import type { VizData } from "@/types/recommendations";

interface Props {
  viz: VizData;
  companyName: string;
}

const SIZE = 520;
const PADDING = 60;
const CENTER = SIZE / 2;
const RADIUS = CENTER - PADDING;

type HoverInfo = {
  cx: number;
  cy: number;
  title: string;
  subtitle?: string;
  tone: "primary" | "amber" | "muted";
};

function toSvg(x: number, y: number) {
  return [CENTER + x * RADIUS, CENTER + y * RADIUS] as const;
}

function scoreColor(score: number) {
  if (score >= 0.85) return "#1e3a66";
  if (score >= 0.7) return "#10b981";
  if (score >= 0.55) return "#a78a3a";
  return "#9ca3af";
}

function scoreRadius(score: number) {
  return 6 + Math.max(0, Math.min(1, (score - 0.5) / 0.5)) * 6;
}

function labelAnchor(angle: number): "start" | "middle" | "end" {
  const norm = ((angle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  if (norm < Math.PI / 4 || norm > (7 * Math.PI) / 4) return "middle";
  if (norm < (3 * Math.PI) / 4) return "start";
  if (norm < (5 * Math.PI) / 4) return "middle";
  return "end";
}

export function EmbeddingSpaceViz({ viz, companyName }: Props) {
  const [hover, setHover] = useState<HoverInfo | null>(null);
  if (!viz || !viz.anchors?.length) return null;

  const cx = toSvg(viz.company.x, viz.company.y);

  return (
    <section className="mx-auto max-w-[1140px] px-5 sm:px-8 py-10 sm:py-14">
      <div className="rounded-2xl border border-border bg-card p-5 sm:p-7">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-[20px] sm:text-[24px] font-extrabold text-foreground tracking-tight">
            임베딩 공간에서 본 위치
          </h2>
          <span className="text-[11.5px] text-muted-foreground font-medium">
            v0.4 · 실험
          </span>
        </div>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-4 break-keep">
          위치는 의미 좌표입니다. 가까이 보여도 점수와는 별개로, 어느 영역에 가까운지만 보여줍니다.
          색·크기는 매칭 점수예요.
        </p>

        <div
          className="relative flex justify-center"
          onMouseLeave={() => setHover(null)}
        >
          <svg
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            width="100%"
            style={{ maxWidth: SIZE }}
            role="img"
            aria-label={`${companyName}의 임베딩 공간 위치`}
          >
            <circle
              cx={CENTER}
              cy={CENTER}
              r={RADIUS}
              fill="#f9fafb"
              stroke="#e5e7eb"
              strokeWidth={1}
            />
            <circle
              cx={CENTER}
              cy={CENTER}
              r={RADIUS * 0.5}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={1}
              strokeDasharray="3 4"
            />

            {/* anchor */}
            {viz.anchors.map((a) => {
              const [ax, ay] = toSvg(a.x, a.y);
              const angle = Math.atan2(a.y, a.x);
              const lx = CENTER + a.x * (RADIUS + 22);
              const ly = CENTER + a.y * (RADIUS + 22);
              return (
                <g key={a.key}>
                  <circle
                    cx={ax}
                    cy={ay}
                    r={10}
                    fill="transparent"
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() =>
                      setHover({
                        cx: ax,
                        cy: ay,
                        title: a.label,
                        subtitle: "도메인 anchor — 의미 좌표의 고정 기준점",
                        tone: "muted",
                      })
                    }
                  />
                  <circle cx={ax} cy={ay} r={4} fill="#9ca3af" pointerEvents="none" />
                  <text
                    x={lx}
                    y={ly}
                    textAnchor={labelAnchor(angle)}
                    dominantBaseline="middle"
                    fontSize={12}
                    fontWeight={600}
                    fill="#374151"
                    pointerEvents="none"
                  >
                    {a.label}
                  </text>
                </g>
              );
            })}

            {/* 결과 점 */}
            {viz.results.map((r) => {
              const [rx, ry] = toSvg(r.x, r.y);
              const rad = scoreRadius(r.score);
              return (
                <circle
                  key={`${r.bid_ntce_no}-${r.bid_ntce_ord}`}
                  cx={rx}
                  cy={ry}
                  r={rad}
                  fill={scoreColor(r.score)}
                  fillOpacity={0.7}
                  stroke="#fff"
                  strokeWidth={1.5}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() =>
                    setHover({
                      cx: rx,
                      cy: ry,
                      title: r.bid_ntce_nm ?? "—",
                      subtitle: `매칭 점수 ${(r.score * 100).toFixed(0)}`,
                      tone: r.score >= 0.7 ? "primary" : "amber",
                    })
                  }
                />
              );
            })}

            {/* 회사 점 — 강조 */}
            <g>
              <circle
                cx={cx[0]}
                cy={cx[1]}
                r={20}
                fill="none"
                stroke="#1e3a66"
                strokeOpacity={0.3}
                strokeWidth={2}
                pointerEvents="none"
              />
              <circle
                cx={cx[0]}
                cy={cx[1]}
                r={14}
                fill="#1e3a66"
                stroke="#fff"
                strokeWidth={3}
                style={{ cursor: "pointer" }}
                onMouseEnter={() =>
                  setHover({
                    cx: cx[0],
                    cy: cx[1],
                    title: companyName,
                    subtitle: "회사 위치 — 등록업종·공급물품·수주 임베딩 평균",
                    tone: "primary",
                  })
                }
              />
              <text
                x={cx[0]}
                y={cx[1] + 32}
                textAnchor="middle"
                fontSize={12}
                fontWeight={700}
                fill="#1e3a66"
                pointerEvents="none"
              >
                {companyName}
              </text>
            </g>
          </svg>

          {/* floating tooltip — SVG viewBox 좌표를 컨테이너 상대 위치로 환산 */}
          {hover && (
            <div
              className={[
                "pointer-events-none absolute z-10 max-w-[260px] rounded-md px-3 py-2 shadow-md border text-[12px] leading-snug",
                hover.tone === "primary"
                  ? "bg-[#1e3a66] text-white border-[#1e3a66]"
                  : hover.tone === "amber"
                    ? "bg-amber-50 text-amber-900 border-amber-300"
                    : "bg-white text-foreground border-border",
              ].join(" ")}
              style={{
                // SVG viewBox 좌표 → 비율(SIZE) → 컨테이너 max-width의 비율
                left: `calc(${(hover.cx / SIZE) * 100}% + 12px)`,
                top: `calc(${(hover.cy / SIZE) * 100}% - 10px)`,
              }}
            >
              <div className="font-bold break-keep">{hover.title}</div>
              {hover.subtitle && (
                <div className={hover.tone === "primary" ? "opacity-90 mt-0.5" : "text-muted-foreground mt-0.5"}>
                  {hover.subtitle}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 text-[11.5px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#1e3a66]" />
            회사
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#1e3a66] opacity-70" />
            점수 85+
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#3f9a5f] opacity-70" />
            점수 70+
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#a78a3a] opacity-70" />
            점수 55+
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-[#9ca3af]" />
            도메인 anchor
          </span>
        </div>
      </div>
    </section>
  );
}
