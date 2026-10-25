// frontend/src/app/(renewal)/about/page.tsx
// 서비스 소개 — 리뉴얼 문법으로 다시 그림(2026-10-25). 09 컷오버는 nav·footer 껍데기만 바꾸고 본문은 옛 개찰판
// (청색 밴드 `gc-*`, "적합 72" 점수 숫자, 폐기된 "검토 여유 +10" 보너스, "넣으면" 구어)을 그대로 두었었다.
// 규칙(docs/design/README.md): 바닥 위 머리 + 흰 판, 먹 괘선은 머리 아래 하나, 주황은 선, 적합 점수 숫자 비노출, 공문 톤.
// 점수표·단계 설명은 lib/how-we-pick.ts 하나만 참조한다(score.py 와 check_changelog.py 가 대조) — 여기에 숫자를 다시 적지 않는다.
// 예시 표는 실제 결과(data/sample.json, 한종산업개발 2026-10-16) 2건 — 가짜 공고·가짜 점수를 만들지 않는다.
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel, PanelHead } from "@/components/Panel";
import { SheetExpand, SheetHead, SheetRow } from "@/components/Sheet";
import { getEntryData } from "@/lib/entry";
import { dLeft, won } from "@/lib/format";
import { NEGATIVE, NOTE, POSITIVE, steps } from "@/lib/how-we-pick";
import { fetchAboutStats, type AboutStats } from "@/lib/notice";

export const metadata: Metadata = {
  title: "조달핏이란 — 나라장터 공고 탐색 서비스",
  description:
    "조달핏은 회사의 등록업종·공급물품·수주 이력을 분석해 검토할 만한 나라장터 공고를 찾아주는 서비스입니다. 추천 방식과 데이터 출처도 확인할 수 있습니다.",
  alternates: { canonical: "/about" },
};

export const revalidate = 3600;

const nf = new Intl.NumberFormat("ko-KR");
const n = (v: number) => (v > 0 ? nf.format(v) : "—");

export default async function AboutPage() {
  const [stats, entry] = await Promise.all([
    fetchAboutStats().catch<AboutStats>(() => ({ activeNotices: 0, totalNotices: 0, companies: 0, contracts: 0 })),
    getEntryData().catch(() => null),
  ]);
  // "지금 입찰 가능"은 입구와 같은 정의(0057 funnel_counts) — 단순 마감일 집계(activeNotices)는 낼 수 없는 공고를 센다.
  const active = entry?.active ?? 0;

  return (
    <>
      <PageHead title="조달핏이란" meta={["나라장터 공공데이터 기반", "공고 매시 · 회사·계약 매일 05:00 갱신"]}>
        <p className="mb-0 mt-5 max-w-[720px] text-[15.5px] leading-[1.75] text-ink-body break-keep">
          회사명 또는 사업자등록번호 하나로 등록업종·공급물품·수주 이력을 읽고, 지금 입찰 가능한 공고 가운데
          참가 자격이 있고 회사와 비슷한 공고를 적합 순으로 정리합니다. 왜 그 순서인지 행마다 근거를 적습니다.
          낙찰 가능성을 예측하지 않습니다 — 검토 시간을 줄이는 도구입니다.
        </p>
        <dl className="mb-0 mt-7 grid grid-cols-4 gap-x-6 gap-y-5 max-sm:grid-cols-2">
          {[
            { k: "지금 입찰 가능한 공고", v: n(active), s: "건", h: "마감 90일 이내 · 참가자격 등록 전" },
            { k: "누적 공고", v: n(stats.totalNotices), s: "건", h: "2026년 이후 전량 벡터화" },
            { k: "등록 회사", v: n(stats.companies), s: "개사", h: "조달업체 등록정보" },
            { k: "계약 이력", v: n(stats.contracts), s: "건", h: "수주 신호의 원천" },
          ].map((d) => (
            <div key={d.k}>
              <dt className="t-k">{d.k}</dt>
              <dd className="m-0 mt-1 flex items-baseline gap-1 text-ink">
                <span className="num text-[28px] font-semibold leading-none tracking-[-0.03em] max-sm:text-[24px]">{d.v}</span>
                <span className="text-[13px] font-medium text-ink-g">{d.s}</span>
              </dd>
              <dd className="m-0 mt-1 text-[12px] text-ink-mute break-keep">{d.h}</dd>
            </div>
          ))}
        </dl>
      </PageHead>

      <Sample />
      <HowWePick active={active} />
      <Comparison />
      <Sources stats={stats} />
      <Limits />
      <Contact />
    </>
  );
}

/* ── 무엇을 합니다 — 말 대신 실제 결과 행 둘 ─────────────────────────── */

// data/sample.json(한종산업개발, 2026-10-16) results[0]·[1]. dev/foundation 의 표본과 같은 행.
const SAMPLE_TODAY = new Date(2026, 9, 16);
const SAMPLE_ROWS = [
  {
    no: 1, title: "송탄정수장 공업용수공급 시설공사(1공구)", org: "경기도 평택시 상하수도사업소", why: "재출현 기관", clse: "2026-10-29", price: 5025454546,
    quals: [{ state: "none", text: "면허 — 제한 없음" }, { state: "none", text: "지역 — 제한 없음" }] as const,
    whys: ["경기도 평택시 상하수도사업소 — 과거 거래 이력 있음", "추정가가 회사 평균 수주가의 1.08배 — 유사한 규모", "공고 내용과 회사 업종 설명 유사도 73%"],
  },
  { no: 2, title: "중랑물재생센터 제1처리장 관리대행", org: "서울특별시 물재생센터 중랑물재생센터", why: "업종·물품 일치", clse: "2026-11-25", price: 6106074545, quals: [], whys: [] },
];

function Sample() {
  return (
    <Panel className="mt-[22px]">
      <PanelHead title="무엇을 합니다" summary={["예시 — 2026-10-16 한종산업개발 결과 중 2건", "실제 값은 회사마다 다름"]} />
      <p className="mb-0 mt-4 max-w-[760px] text-[14.5px] leading-[1.75] text-ink-body break-keep">
        회사명 또는 사업자등록번호를 입력하면 진행 중 공고가 회사 기준 적합 순으로 정렬됩니다. 행을 펼치면{" "}
        <b className="font-semibold text-ink">참가 자격 판정</b>과 <b className="font-semibold text-ink">추천 근거</b>가 나오고,
        첨부 문서가 있으면 과업·자격·일정 요약이 함께 붙습니다. 점수 숫자는 보여주지 않습니다 — 순서가 곧 적합도입니다.
      </p>
      <div className="mt-5">
        <SheetHead />
        {SAMPLE_ROWS.map((r) => (
          <SheetRow key={r.no} no={r.no} title={r.title} org={r.org} why={r.why} dLeft={dLeft(r.clse, SAMPLE_TODAY)} price={won(r.price)} defaultOpen={r.no === 1}>
            {r.quals.length > 0 && <SheetExpand quals={[...r.quals]} whys={r.whys} />}
          </SheetRow>
        ))}
      </div>
      <p className="mb-0 mt-4 text-[13px] leading-[1.7] text-ink-g break-keep">
        키워드로도 찾을 수 있습니다 — “교량 점검”, “급식 식자재”처럼 업종 또는 품목을 입력하면 회사 정보 없이 의미가 가까운 공고를 찾습니다.
        회사 정보가 없으므로 참가 자격은 판정하지 않습니다.
      </p>
    </Panel>
  );
}

/* ── 어떻게 고르는가 — lib/how-we-pick.ts 하나만 ───────────────────────── */

function HowWePick({ active }: { active: number }) {
  const st = steps(active);
  return (
    <Panel className="mt-[22px]">
      <PanelHead title="어떻게 고르는가" summary={["운영 점수표 값 그대로", <a key="c" href="/changelog" className="u-link text-ink">개선 기록 →</a>]} />
      <ol className="m-0 list-none p-0">
        {st.map((s, i) => (
          <li key={s.k} className="grid grid-cols-[36px_220px_minmax(0,1fr)] gap-x-5 border-b border-rule py-4 last:border-b-0 max-sm:grid-cols-[28px_minmax(0,1fr)] max-sm:gap-y-1.5">
            <span className="num pt-0.5 text-[13px] text-ink-mute">{String(i + 1).padStart(2, "0")}</span>
            <div className="min-w-0">
              <div className="text-[15px] font-semibold text-ink break-keep">{s.k}</div>
              <div className="mt-0.5 text-[13px] text-ink-g break-keep"><b className="num font-semibold text-ink">{s.n}</b>{s.n !== "회사마다" && "건"} · {s.sub}</div>
            </div>
            <p className="m-0 text-[14px] leading-[1.7] text-ink-body break-keep max-sm:col-start-2">{s.d}</p>
          </li>
        ))}
      </ol>
      <div className="mt-6 grid grid-cols-2 gap-x-8 gap-y-5 border-t border-rule pt-5 max-sm:grid-cols-1">
        {[{ k: "올리는 것", rows: POSITIVE }, { k: "내리는 것", rows: NEGATIVE }].map((g) => (
          <div key={g.k}>
            <span className="t-k mb-1.5 block">{g.k}</span>
            <ul className="m-0 list-none p-0" data-factors>
              {g.rows.map((f) => (
                <li key={f.t} className="flex items-baseline justify-between gap-4 border-b border-rule py-2 text-[14px] last:border-b-0">
                  <span className="text-ink-body break-keep">{f.t}{f.d && <span className="ml-1.5 text-[12.5px] text-ink-mute">({f.d})</span>}</span>
                  <b className="num shrink-0 font-semibold text-ink">{f.v}</b>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="mb-0 mt-5 text-[13px] leading-[1.7] text-ink-g break-keep">{NOTE}</p>
    </Panel>
  );
}

/* ── 키워드 알림과 다른 점 ─────────────────────────────────────────── */

const COMPARE: [string, string, string][] = [
  ["찾는 방식", "등록한 단어가 제목에 있을 때", "회사 영역과 뜻이 가까울 때 — 단어가 달라도"],
  ["회사를 아는 정도", "키워드 목록", "등록업종·공급물품 + 실제 수주 이력"],
  ["참가 자격", "직접 확인", "허용업종·지역·등록 마감을 먼저 대조해 제외"],
  ["추천 근거", "없음", "행마다 가장 강한 신호 1개, 펼치면 근거 전부"],
  ["첨부 문서", "직접 내려받아 읽기", "과업·자격·일정 요약 + 원문 링크"],
  ["공고가 바뀌면", "새 알림", "정정 차수와 바뀐 항목 비교"],
];

function Comparison() {
  return (
    <Panel className="mt-[22px]">
      <PanelHead title="키워드 알림과 다른 점" />
      <table className="w-full border-collapse text-[14px] max-sm:hidden">
        <thead>
          <tr className="border-b border-rule text-left">
            <th className="t-k w-[150px] py-2.5 pr-4 font-semibold">항목</th>
            <th className="t-k w-[36%] py-2.5 pr-4 font-semibold">키워드 알림</th>
            <th className="py-2.5 text-[13px] font-semibold text-ink">조달핏</th>
          </tr>
        </thead>
        <tbody>
          {COMPARE.map(([k, a, b]) => (
            <tr key={k} className="border-b border-rule align-top last:border-b-0">
              <th scope="row" className="py-3 pr-4 text-left font-semibold text-ink-sub">{k}</th>
              <td className="py-3 pr-4 text-ink-g break-keep">{a}</td>
              <td className="py-3 font-medium text-ink break-keep">{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="m-0 hidden list-none p-0 max-sm:block">
        {COMPARE.map(([k, a, b]) => (
          <li key={k} className="border-b border-rule py-3.5 last:border-b-0">
            <div className="t-k">{k}</div>
            <div className="mt-1.5 grid grid-cols-[72px_minmax(0,1fr)] gap-x-3 gap-y-1 text-[14px]">
              <span className="text-[12px] text-ink-mute">키워드 알림</span><span className="text-ink-g break-keep">{a}</span>
              <span className="text-[12px] font-semibold text-ink">조달핏</span><span className="font-medium text-ink break-keep">{b}</span>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/* ── 데이터 출처 ───────────────────────────────────────────────────── */

// 갱신 주기는 .github/workflows 의 세 잡과 같다 — hourly(공고) / documents 2시간(첨부) / daily 05:00(나머지)
const SOURCES: [string, string, string][] = [
  ["입찰공고 · 첨부 목록", "입찰공고정보", "매시"],
  ["첨부 문서 본문 · 요약", "첨부 원문에서 추출", "2시간"],
  ["계약 · 낙찰 · 개찰 참가", "계약정보 · 낙찰정보", "매일 05:00"],
  ["회사 등록정보 · 등록업종 · 공급물품", "조달업체정보", "매일 05:00"],
  ["허용업종 · 참가 가능 지역 제한", "입찰공고정보", "매일 05:00"],
  ["사전규격 · 의견 · 발주계획", "사전규격정보 · 발주계획정보", "매일 05:00"],
  ["부정당 제재", "조달업체정보", "매일 05:00"],
];

function Sources({ stats }: { stats: AboutStats }) {
  return (
    <Panel className="mt-[22px]">
      <PanelHead title="데이터 출처" summary={["조달청 나라장터 공공데이터 API", <>누적 공고 <b>{n(stats.totalNotices)}</b>건</>]} />
      <p className="mb-0 mt-4 max-w-[760px] text-[14.5px] leading-[1.75] text-ink-body break-keep">
        전부 <a href="https://www.data.go.kr" target="_blank" rel="noreferrer" className="u-link font-semibold text-ink">공공데이터포털</a>이 공개하는 공식 API 입니다.
        회사가 나라장터에 등록한 정보가 원본이라, 그쪽에서 고치면 다음 갱신 때 조달핏에도 반영됩니다. 첨부 문서는 원본을 저장하지 않고
        추출한 텍스트만 보관하며, 원문 링크를 항상 함께 둡니다.
      </p>
      <table className="mt-4 w-full border-collapse text-[14px]">
        <thead>
          <tr className="border-b border-rule text-left">
            <th className="t-k py-2.5 pr-4 font-semibold">데이터</th>
            <th className="t-k py-2.5 pr-4 font-semibold max-sm:hidden">API 서비스</th>
            <th className="t-k w-[96px] py-2.5 text-right font-semibold">갱신</th>
          </tr>
        </thead>
        <tbody>
          {SOURCES.map(([d, s, c]) => (
            <tr key={d} className="border-b border-rule last:border-b-0">
              <td className="py-3 pr-4 font-medium text-ink break-keep">
                {d}<span className="mt-0.5 hidden text-[12.5px] font-normal text-ink-mute max-sm:block">{s}</span>
              </td>
              <td className="py-3 pr-4 text-ink-g break-keep max-sm:hidden">{s}</td>
              <td className="num whitespace-nowrap py-3 text-right text-ink-sub">{c}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

/* ── 할 수 없는 것 ─────────────────────────────────────────────────── */

const LIMITS: [string, string][] = [
  ["낙찰을 예측하지 않습니다", "추천 순서는 검토할 공고를 놓치지 않기 위한 순서이며 낙찰 확률이 아닙니다. 낙찰 확률 같은 숫자는 어디에도 쓰지 않습니다."],
  ["참가 자격은 공고 필드만 판정합니다", "허용업종·참가 가능 지역·참가자격 등록 마감 세 가지를 대조합니다. 첨부 문서에 적힌 실적·증명 요건은 판정하지 않고 보여만 주므로, 최종 확인은 공고 원문으로 해야 합니다."],
  ["문서 요약은 원문을 대신하지 않습니다", "첨부 문서 요약은 문서에 적힌 내용만 옮기지만 읽기 오류가 있을 수 있습니다. 요약 옆에 원문 링크를 항상 둡니다."],
  ["회사 등록정보가 없으면 정확도가 낮습니다", "나라장터에 등록업종이 없는 회사는 면허 자격을 판정하지 못하며, 그 사실을 결과 화면에 적습니다. 그런 회사는 키워드 검색이 더 맞습니다."],
];

function Limits() {
  return (
    <Panel className="mt-[22px]">
      <PanelHead title="할 수 없는 것, 보장하지 않는 것" summary={["최종 판단은 사람이 합니다"]} />
      <ul className="m-0 list-none p-0">
        {LIMITS.map(([t, b]) => (
          <li key={t} className="grid grid-cols-[280px_minmax(0,1fr)] gap-x-6 gap-y-1 border-b border-rule py-4 last:border-b-0 max-sm:grid-cols-1">
            <h3 className="m-0 text-[15px] font-semibold text-ink break-keep">{t}</h3>
            <p className="m-0 text-[14px] leading-[1.75] text-ink-body break-keep">{b}</p>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/* ── 연락처 + 다음 행동 ─────────────────────────────────────────────── */

function Contact() {
  return (
    <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-ink pt-5">
      <p className="m-0 text-[14px] text-ink-g break-keep">
        문의 · 제안 · 오류 제보 <a href="mailto:jsw7980@gmail.com" className="u-link ml-1 font-medium text-ink">jsw7980@gmail.com</a>
      </p>
      <Btn variant="dark" href="/">회사로 찾기</Btn>
    </div>
  );
}
