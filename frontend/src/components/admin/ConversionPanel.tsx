import { Panel, PanelHead } from "@/components/Panel";
import type { Conversions } from "@/lib/admin-conversion";

const nf = new Intl.NumberFormat("ko-KR");
const pct = (v: number | null) => v == null ? "—" : `${(v * 100).toFixed(v * 100 >= 10 ? 0 : 1)}%`;

export function ConversionPanel({ data }: { data: Conversions }) {
  return (
    <Panel className="mt-[14px]" data-admin="conversions">
        <PanelHead title="결과 이후 전환" small="오늘 / 오늘 포함 7일 · 같은 탭 기준" />
        {data.error ? <p className="m-0 pt-5 text-[14px] text-ink-mute">전환을 읽지 못했습니다 — {data.error}</p> : <>
          <Table head={["행동", "오늘 세션", "오늘 비율", "7일 세션", "7일 비율"]}
            rows={([
              ["결과 조회", "results", "results"],
              ["공고 열기", "opened", "results"],
              ["저장 시도", "intent", "results"],
              ["저장 성공", "saved", "intent"],
              ["비로그인 저장 시도", "guestIntent", "results"],
              ["저장 시도 후 가입 화면", "signup", "guestIntent"],
            ] as const).map(([label, key, denominator]) => {
              const a = data.today, b = data.week;
              return [label, nf.format(a[key]), pct(a[denominator] ? a[key] / a[denominator] : null), nf.format(b[key]), pct(b[denominator] ? b[key] / b[denominator] : null)];
            })} />
          <p className="mb-0 mt-3 text-[12px] leading-[1.7] text-ink-mute">
            결과 조회 이후 행동을 탭마다 한 번 셉니다. 공고를 열지 않고 바로 저장한 경우도 포함합니다.
            저장 성공률은 저장 시도 대비, 가입 화면 진입률은 비로그인 저장 시도 대비이며 나머지는 결과 조회 대비입니다.
            가입 화면 진입은 가입 완료가 아닙니다. 가입 완료는 Auth에서 별도로 확인합니다.
            새 계측 배포 이후부터 누적하며 내부 SSR·로컬 검증·알려진 봇은 제외합니다. 브라우저 계측 차단·다른 탭 이동은 연결되지 않을 수 있습니다.
          </p>
          {data.truncated && <p className="mb-0 mt-2 text-[13px] text-orange-ink">조회 상한 10,000건에 도달했습니다. 위 수치는 일부 이벤트 기준입니다.</p>}
        </>}
      </Panel>
  );
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return <div className="overflow-x-auto pt-2"><table className="w-full border-collapse text-[13.5px] leading-[1.5]">
    <thead><tr className="rule-ink text-left text-[12px] text-ink-dim">{head.map((h, i) => <th key={h} className={`whitespace-nowrap py-2 pr-4 font-semibold ${i ? "text-right" : ""}`}>{h}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i} className="border-b border-rule">{row.map((cell, j) => <td key={j} className={`whitespace-nowrap py-2 pr-4 ${j ? "num text-right" : "text-ink-g"}`}>{cell}</td>)}</tr>)}</tbody>
  </table></div>;
}
