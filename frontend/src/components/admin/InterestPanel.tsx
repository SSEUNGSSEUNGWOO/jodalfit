import { Panel, PanelHead } from "@/components/Panel";
import type { Interest } from "@/lib/admin";

const nf = new Intl.NumberFormat("ko-KR");
const ratio = (n: number, d: number) => d ? `${(n / d * 100).toFixed(1)}%` : "—";

export function InterestPanel({ data }: { data: Interest }) {
  return <Panel id="admin-interest" className="mt-[14px] scroll-mt-6" data-admin="interest">
    <PanelHead title="제안서 작성 준비안 수요" small="최근 30일 · 공고 상세" />
    {data.error ? <p role="status" className="m-0 pt-5 text-[14px] text-ink-g">기능 관심 집계를 읽지 못했습니다. 관심이 0이라는 뜻은 아닙니다.</p> : <>
      <dl className="m-0 grid grid-cols-4 gap-5 pt-5 max-sm:grid-cols-2">
        {[
          ["버튼 노출", data.views, "화면에 들어온 횟수"], ["관심 클릭", data.registers, `노출 대비 ${ratio(data.registers, data.views)}`],
          ["등록한 고유 회원", data.registeredUsers, "로그인 상태로 등록"], ["비로그인 클릭", data.anonRegisters, "회원 등록 완료와 별도"],
        ].map(([label, value, hint]) => <div key={String(label)}><dt className="t-k">{label}</dt><dd className="num m-0 mt-2 text-[24px] font-semibold text-ink">{nf.format(Number(value))}</dd><dd className="m-0 mt-1 text-[12px] text-ink-mute">{hint}</dd></div>)}
      </dl>
      {data.byDiv.length > 0 ? <div className="overflow-x-auto pt-5"><table className="w-full border-collapse text-[13px]">
        <thead><tr className="rule-ink text-left">{["업무구분", "노출", "관심 클릭", "노출 대비"].map((label) => <th key={label} className="whitespace-nowrap py-2 pr-4 font-semibold">{label}</th>)}</tr></thead>
        <tbody>{data.byDiv.map((row) => <tr key={row.div} className="border-b border-rule"><td className="py-2 pr-4">{row.div}</td><td className="num py-2 pr-4">{nf.format(row.views)}</td><td className="num py-2 pr-4">{nf.format(row.registers)}</td><td className="num py-2 pr-4">{ratio(row.registers, row.views)}</td></tr>)}</tbody>
      </table></div> : <p className="mb-0 mt-4 text-[13px] text-ink-g">아직 노출·등록 기록이 없습니다.</p>}
      <p className="mb-0 mt-4 text-[12px] leading-[1.7] text-ink-mute">많이 노출된 업무구분은 클릭 수도 많아질 수 있습니다. 노출 대비 비율과 고유 회원 수를 함께 봅니다. 관심 클릭은 실제 사용이나 결제 의사가 아니며, 비로그인 클릭을 가입 이탈로 단정하지 않습니다.</p>
    </>}
  </Panel>;
}
