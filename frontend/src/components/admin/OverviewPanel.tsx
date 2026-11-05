import { Panel, PanelHead } from "@/components/Panel";
import type { AdminOverview } from "@/lib/admin-summary";

const nf = new Intl.NumberFormat("ko-KR");
const number = (value: number, available: boolean) => available ? nf.format(value) : "—";
const percent = (a: number, b: number) => b ? `${(a / b * 100).toFixed(1)}%` : "—";
const change = (a: number, b: number) => b ? `전주 ${nf.format(b)} · ${a >= b ? "+" : ""}${((a - b) / b * 100).toFixed(1)}%` : `전주 ${nf.format(b)} · 증감률 비교 불가`;

export function OverviewPanel({ data }: { data: AdminOverview }) {
  const { pulse: p, members: m, searches: s } = data;
  const visitsOk = !p.error;
  const memberOk = data.membersAvailable;
  const searchOk = data.searchesAvailable;
  return <div data-admin="overview" className="mt-[22px]">
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="m-0 text-[18px] font-semibold text-ink">최근 완료 7일 <span className="num ml-2 text-[13px] font-normal text-ink-g">{data.from} ~ {data.through}</span></h2>
      <span className="text-[12px] text-ink-mute">비교 기간: {data.previousFrom}부터 7일 · 오늘 제외</span>
    </div>
    {(data.issues.length > 0 || p.error) && <div role="status" className="mb-4 rounded-[8px] border border-field bg-panel px-4 py-3 text-[13px] leading-[1.7] text-ink-g">
      <b className="font-semibold text-ink">일부 집계를 확인하지 못했습니다.</b>
      <ul className="m-0 mt-1 list-disc pl-5">{[...data.issues, ...(p.error ? [`방문·원문 이동·재방문: ${p.error}`] : [])].map((issue) => <li key={issue}>{issue}</li>)}</ul>
      조회 실패는 0으로 판단하지 않습니다.
    </div>}
    <dl className="m-0 grid grid-cols-4 gap-3 max-md:grid-cols-2">
      {[
        { label: "방문", value: number(p.visitors, visitsOk), unit: "브라우저", hint: visitsOk ? change(p.visitors, p.previousVisitors) : "방문 집계 조회 불가", sub: visitsOk ? `페이지뷰 ${nf.format(p.views)}회` : "" },
        { label: "검색한 방문자", value: number(p.searchers, visitsOk), unit: "브라우저", hint: visitsOk ? `결과를 본 방문자 ${nf.format(p.resultViewers)}개` : "행동 집계 조회 불가", sub: "검색·결과 확인은 각각 고유 브라우저 기준" },
        { label: "새 가입", value: number(m.newMembers, memberOk), unit: "계정", hint: memberOk ? change(m.newMembers, m.previousNewMembers) : "회원 집계 조회 불가", sub: "인증 전 계정 포함 · 관리자·테스트 제외" },
        { label: "나라장터 원문 이동", value: number(p.outboundUsers, visitsOk), unit: "브라우저", hint: visitsOk ? `원문·첨부 링크 ${nf.format(p.outboundClicks)}회` : "원문 이동 조회 불가", sub: "공고 페이지 직접 방문도 포함" },
      ].map((card) => <div key={card.label} className="min-w-0 rounded-[12px] border border-hair bg-panel px-5 py-5 max-sm:px-4">
        <dt className="text-[13px] font-medium text-ink-g">{card.label}</dt>
        <dd className="m-0 mt-2 flex flex-wrap items-baseline gap-1.5"><b className="num text-[29px] font-semibold leading-none tracking-[-0.03em] text-ink max-sm:text-[25px]">{card.value}</b><span className="text-[12px] text-ink-mute">{card.unit}</span></dd>
        <dd className="m-0 mt-3 text-[12.5px] leading-[1.6] text-ink-g">{card.hint}</dd>
        <dd className="m-0 mt-1 text-[11.5px] leading-[1.6] text-ink-mute">{card.sub}</dd>
      </div>)}
    </dl>

    <div className="mt-3 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
      <Panel data-admin="retention">
        <PanelHead title="다시 방문하는가" small="두 주 사이의 재방문" />
        <p className="mb-0 mt-5"><b className="num text-[30px] font-semibold tracking-[-0.03em] text-ink">{visitsOk ? percent(p.returning, p.previousVisitors) : "—"}</b></p>
        <p className="mb-0 mt-2 text-[13.5px] leading-[1.7] text-ink-g">{visitsOk ? <>전주 방문 브라우저 <b className="num text-ink">{nf.format(p.previousVisitors)}</b>개 중 <b className="num text-ink">{nf.format(p.returning)}</b>개가 최근 7일에도 방문했습니다.</> : "방문 데이터를 읽지 못해 재방문을 판단할 수 없습니다."}</p>
        <p className="mb-0 mt-2 text-[12px] leading-[1.7] text-ink-mute">주간 방문자의 겹침이며 가입자 D7 리텐션이 아닙니다. 같은 사람이 기기를 바꾸면 다르게 집계될 수 있습니다.</p>
      </Panel>
      <Panel data-admin="search-problems">
        <PanelHead title="검색에서 막히는가" small="검색 로그 기준" />
        <p className="mb-0 mt-5"><b className="num text-[30px] font-semibold tracking-[-0.03em] text-ink">{searchOk ? percent(s.problems, s.total) : "—"}</b><span className="ml-2 text-[13px] text-ink-g">{searchOk ? `${nf.format(s.total)}회 중 ${nf.format(s.problems)}회` : "검색 조회 불가"}</span></p>
        <p className="mb-0 mt-2 text-[13px] leading-[1.7] text-ink-g">{searchOk ? <>회사 식별 실패 <b className="num text-ink">{s.missingCompany}</b> · 등록정보 부족 <b className="num text-ink">{s.missingProfile}</b> · 기타 <b className="num text-ink">{s.other}</b></> : "검색 데이터를 읽지 못해 문제 비율을 판단할 수 없습니다."}</p>
        <p className="mb-0 mt-2 text-[12px] leading-[1.7] text-ink-mute">회사 검색 실패 뒤 키워드 검색으로 이어질 수 있습니다. 모두 서버 장애라는 뜻은 아닙니다.</p>
        <a href="#admin-problems" className="mt-3 inline-block border-b border-field text-[13px] font-medium text-ink hover:border-orange">문제가 기록된 검색 확인 ↓</a>
      </Panel>
    </div>

    <Panel className="mt-3" data-admin="activation">
      <PanelHead title="가입 후 실제로 쓰는가" small="현재 누적 · 회원 DB 기준" />
      <dl className="m-0 grid grid-cols-4 gap-x-5 gap-y-5 pt-5 max-sm:grid-cols-2">
        {[
          ["전체 회원", m.total, "계정"], ["인증 완료", m.confirmed, "계정"],
          ["회사 저장 회원", m.companyUsers, "명"], ["공고 저장 회원", m.noticeUsers, "명"],
        ].map(([label, value, unit]) => <div key={String(label)}><dt className="t-k">{label}</dt><dd className="m-0 mt-2"><b className="num text-[24px] font-semibold text-ink">{number(Number(value), memberOk)}</b><span className="ml-1 text-[12px] text-ink-g">{unit}</span></dd></div>)}
      </dl>
      <p className="mb-0 mt-4 text-[12.5px] leading-[1.7] text-ink-g">{memberOk ? <>현재 보관 중인 회사 {m.companies}건 · 공고 {m.notices}건 · 관리자·테스트 {m.excluded}계정 제외. </> : "회원·저장 데이터를 모두 읽지 못했습니다. "}저장을 해제한 기록은 포함하지 않습니다. 원문으로 바로 이동한 사용자도 있으므로 저장만으로 서비스 가치를 판단하지 않습니다.</p>
    </Panel>
    <p className="mb-0 mt-3 text-[12px] leading-[1.7] text-ink-mute">방문·검색·원문 이동은 브라우저 계측, 가입·저장은 회원 DB에서 읽습니다. 서로 다른 숫자를 나눈 가입 전환율은 만들지 않습니다. 방문 집계는 최대 5분 지연되며 관리자·개발 페이지를 제외합니다. 익명 방문에서 운영자·봇을 완전히 구분하지 못할 수 있습니다.</p>
  </div>;
}
