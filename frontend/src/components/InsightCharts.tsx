import type { ChartDatum } from "@/lib/insights";

const PRIMARY = "#047857";
const PALETTE = ["#047857", "#10b981", "#5eead4", "#a7f3d0", "#d1fae5"];

function sum(data: ChartDatum[]) {
  return data.reduce((s, d) => s + d.value, 0);
}

export function DonutChart({ title, data }: { title: string; data: ChartDatum[] }) {
  const total = sum(data);
  if (!total) return null;

  const cx = 110;
  const cy = 110;
  const r = 80;
  const strokeWidth = 28;
  const circumference = 2 * Math.PI * r;

  let cumulative = 0;
  const arcs = data.map((d, i) => {
    const portion = d.value / total;
    const dash = portion * circumference;
    const gap = circumference - dash;
    const offset = -cumulative;
    cumulative += dash;
    return {
      key: i,
      label: d.label,
      value: d.value,
      portion,
      dash,
      gap,
      offset,
      color: PALETTE[i % PALETTE.length],
    };
  });

  return (
    <div className="my-6 rounded-lg border border-border bg-card p-5">
      <div className="text-[13px] font-semibold text-muted-foreground mb-3">{title}</div>
      <div className="flex flex-col sm:flex-row items-center gap-5">
        <svg width={220} height={220} viewBox="0 0 220 220" className="shrink-0">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f3f4f6" strokeWidth={strokeWidth} />
          {arcs.map((a) => (
            <circle
              key={a.key}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={a.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${a.dash} ${a.gap}`}
              strokeDashoffset={a.offset}
              transform={`rotate(-90 ${cx} ${cy})`}
            />
          ))}
          <text x={cx} y={cy - 4} textAnchor="middle" className="fill-foreground" fontSize="22" fontWeight="700">
            {total.toLocaleString()}
          </text>
          <text x={cx} y={cy + 16} textAnchor="middle" className="fill-muted-foreground" fontSize="11">
            합계
          </text>
        </svg>
        <ul className="flex-1 space-y-2 text-[14px]">
          {arcs.map((a) => (
            <li key={a.key} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2">
                <span className="inline-block size-3 rounded-sm" style={{ background: a.color }} />
                <span className="text-foreground">{a.label}</span>
              </span>
              <span className="text-muted-foreground tabular-nums">
                {a.value.toLocaleString()} · {(a.portion * 100).toFixed(1)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function HorizontalBarChart({
  title,
  data,
}: {
  title: string;
  data: ChartDatum[];
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="my-6 rounded-lg border border-border bg-card p-5">
      <div className="text-[13px] font-semibold text-muted-foreground mb-3">{title}</div>
      <ul className="space-y-3 text-[14px]">
        {data.map((d, i) => {
          const pct = (d.value / max) * 100;
          return (
            <li key={i} className="grid grid-cols-[110px_1fr_auto] gap-3 items-center">
              <span className="text-foreground truncate">{d.label}</span>
              <div className="h-6 rounded-sm bg-muted overflow-hidden">
                <div
                  className="h-full rounded-sm"
                  style={{
                    width: `${pct}%`,
                    background: PRIMARY,
                    opacity: 0.85,
                  }}
                />
              </div>
              <span className="text-muted-foreground tabular-nums w-16 text-right">
                {d.value.toLocaleString()}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
