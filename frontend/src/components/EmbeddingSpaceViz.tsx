import type { VizData } from "@/types/recommendations";

interface Props {
  viz: VizData;
  companyName: string;
}

const SIZE = 520;
const PADDING = 60;
const CENTER = SIZE / 2;
const RADIUS = CENTER - PADDING;

function toSvg(x: number, y: number) {
  return [CENTER + x * RADIUS, CENTER + y * RADIUS] as const;
}

function scoreColor(score: number) {
  // 0.5~0.95 → amber → primary 그라데이션
  if (score >= 0.85) return "#166534";
  if (score >= 0.7) return "#3f9a5f";
  if (score >= 0.55) return "#a78a3a";
  return "#9ca3af";
}

function scoreRadius(score: number) {
  // 6~12
  return 6 + Math.max(0, Math.min(1, (score - 0.5) / 0.5)) * 6;
}

function labelAnchor(angle: number): "start" | "middle" | "end" {
  // 라벨이 anchor 점 바깥쪽에 위치하도록 정렬
  const norm = ((angle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  if (norm < Math.PI / 4 || norm > (7 * Math.PI) / 4) return "middle"; // 12시 근처
  if (norm < (3 * Math.PI) / 4) return "start"; // 오른쪽
  if (norm < (5 * Math.PI) / 4) return "middle"; // 6시 근처
  return "end"; // 왼쪽
}

export function EmbeddingSpaceViz({ viz, companyName }: Props) {
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

        <div className="flex justify-center">
          <svg
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            width="100%"
            style={{ maxWidth: SIZE }}
            role="img"
            aria-label={`${companyName}의 임베딩 공간 위치`}
          >
            {/* 가이드 원 */}
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

            {/* anchor 점 + 라벨 */}
            {viz.anchors.map((a) => {
              const [ax, ay] = toSvg(a.x, a.y);
              const angle = Math.atan2(a.y, a.x);
              const lx = CENTER + a.x * (RADIUS + 22);
              const ly = CENTER + a.y * (RADIUS + 22);
              return (
                <g key={a.key}>
                  <circle cx={ax} cy={ay} r={4} fill="#9ca3af" />
                  <text
                    x={lx}
                    y={ly}
                    textAnchor={labelAnchor(angle)}
                    dominantBaseline="middle"
                    fontSize={12}
                    fontWeight={600}
                    fill="#374151"
                  >
                    {a.label}
                  </text>
                </g>
              );
            })}

            {/* 결과 점 (회사 아래에 그려서 회사가 위로 보이게) */}
            {viz.results.map((r) => {
              const [rx, ry] = toSvg(r.x, r.y);
              return (
                <g key={`${r.bid_ntce_no}-${r.bid_ntce_ord}`}>
                  <circle
                    cx={rx}
                    cy={ry}
                    r={scoreRadius(r.score)}
                    fill={scoreColor(r.score)}
                    fillOpacity={0.7}
                    stroke="#fff"
                    strokeWidth={1.5}
                  >
                    <title>{`${r.bid_ntce_nm ?? "-"}\n매칭 점수 ${(r.score * 100).toFixed(0)}`}</title>
                  </circle>
                </g>
              );
            })}

            {/* 회사 점 — 강조 */}
            <g>
              <circle
                cx={cx[0]}
                cy={cx[1]}
                r={14}
                fill="#166534"
                stroke="#fff"
                strokeWidth={3}
              />
              <circle
                cx={cx[0]}
                cy={cx[1]}
                r={20}
                fill="none"
                stroke="#166534"
                strokeOpacity={0.3}
                strokeWidth={2}
              />
              <text
                x={cx[0]}
                y={cx[1] + 32}
                textAnchor="middle"
                fontSize={12}
                fontWeight={700}
                fill="#166534"
              >
                {companyName}
              </text>
            </g>
          </svg>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 text-[11.5px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#166534]" />
            회사
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#166534] opacity-70" />
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
