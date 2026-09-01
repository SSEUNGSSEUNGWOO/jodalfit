import type { Metadata } from "next";
import Link from "next/link";
import { BoardSeal } from "@/components/board/BoardSeal";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { fetchAboutStats, type AboutStats } from "@/lib/notice";

export const metadata: Metadata = {
  title: "조달핏이란 — 나라장터 공고 탐색 서비스",
  description:
    "조달핏은 회사의 등록업종·공급물품·수주 이력을 분석해 검토할 만한 나라장터 공고를 찾아주는 서비스입니다. 추천 방식과 데이터 출처도 확인할 수 있습니다.",
  alternates: { canonical: "/about" },
};

export const revalidate = 3600;

export default async function AboutPage() {
  const stats = await fetchAboutStats().catch<AboutStats>(() => ({
    activeNotices: 0,
    totalNotices: 0,
    companies: 0,
    contracts: 0,
  }));

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <Masthead stats={stats} />
        <SampleBoard />
        <Process />
        <Comparison />
        <Ledger stats={stats} />
        <Limits />
        <Contact />
      </main>
      <Footer className="mt-0" />
    </>
  );
}

/* ── 공통: 이중 괘선 섹션 머리 ─────────────────────────── */

function SectionHead({
  title,
  note,
  id,
}: {
  title: string;
  note?: string;
  id?: string;
}) {
  return (
    <div
      id={id}
      className="gc-double-rule pt-4 pb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 scroll-mt-24"
    >
      <h2 className="font-gc-serif font-black text-[22px] sm:text-[26px] tracking-[-0.02em] text-gc-ink break-keep">
        {title}
      </h2>
      {note && <span className="text-[12.5px] text-gc-ink-3 break-keep">{note}</span>}
    </div>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return (
    <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-14 sm:pt-16">
      {children}
    </section>
  );
}

const n = (v: number) => (v > 0 ? v.toLocaleString("ko-KR") : "—");

/* ── 판머리 — 네이비 밴드 위 제호·표제·규모 ────────────────── */

function Masthead({ stats }: { stats: AboutStats }) {
  return (
    <section className="bg-gc-band">
      <div className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-7 sm:pt-9 pb-12 sm:pb-14">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-gc-band-ink/40 pb-3">
          <span className="font-gc-serif font-black text-[15px] tracking-[0.02em] text-gc-band-hi">
            조달핏
          </span>
          <span className="text-[12px] text-gc-band-ink">
            서비스 안내 · 공공 OpenAPI 기반 · 매시간 갱신
          </span>
        </div>

        <div className="mt-10 sm:mt-14 flex items-start justify-between gap-6">
          <div className="min-w-0 max-w-[760px]">
            <h1 className="font-gc-serif font-black text-[32px] sm:text-[50px] leading-[1.22] tracking-[-0.02em] text-gc-band-hi break-keep">
              나라장터 공고를
              <br />
              회사 기준으로 정리하는 탐색 서비스
            </h1>
            <p className="mt-5 text-[15.5px] sm:text-[17px] leading-[1.7] text-gc-band-ink max-w-[600px] break-keep">
              회사명 하나로 등록업종·공급물품·수주 이력을 읽고, 진행 중 공고를
              검토할 만한 순서로 다시 세웁니다. 왜 그 순서인지도 행마다 적혀
              있습니다. 낙찰을 약속하는 서비스가 아니라, 검토 시간을 줄이는
              도구입니다.
            </p>
          </div>
          <BoardSeal size={72} className="hidden sm:block shrink-0 mt-2" />
        </div>

        {/* 규모 — 데이터가 곧 제품이므로 건수를 숨기지 않는다 */}
        <dl className="mt-10 sm:mt-12 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-5 border-t border-gc-band-ink/40 pt-5">
          {[
            { k: "진행 중 공고", v: n(stats.activeNotices), s: "건", h: "마감 전" },
            { k: "누적 공고", v: n(stats.totalNotices), s: "건", h: "2026년 이후 전량 벡터화" },
            { k: "등록 회사", v: n(stats.companies), s: "개사", h: "조달업체 등록정보" },
            { k: "계약 이력", v: n(stats.contracts), s: "건", h: "수주 시그널의 원천" },
          ].map((d) => (
            <div key={d.k}>
              <dt className="text-[12px] font-bold text-gc-band-ink">{d.k}</dt>
              <dd className="mt-1 flex items-baseline gap-1 text-gc-band-hi">
                <span className="font-gc-serif font-black text-[26px] sm:text-[30px] leading-none tabular tabular-nums tracking-[-0.02em]">
                  {d.v}
                </span>
                <span className="text-[13px] font-bold">{d.s}</span>
              </dd>
              <dd className="mt-1 text-[12px] text-gc-band-ink">{d.h}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

/* ── 무엇을 합니다 — 말 대신 개봉된 행 하나를 보여준다 ────────── */

const SAMPLE_SIGNALS = [
  { label: "유사도 61%", pts: "+61" },
  { label: "재출현 기관", pts: "+50" },
  { label: "지역 매칭", pts: "+30" },
  { label: "검토 여유", pts: "+10" },
];

function SampleBoard() {
  return (
    <Wrap>
      <SectionHead
        title="무엇을 합니다"
        note="아래는 예시 화면 — 실제 값은 회사마다 다릅니다"
      />
      <p className="mt-5 max-w-[720px] text-[15px] leading-[1.8] text-gc-ink-2 break-keep">
        회사명이나 사업자번호를 넣으면 진행 중 공고가 우리 회사 기준 적합도 순으로
        한 판에 정렬됩니다. 행을 열면 <strong className="text-gc-ink">점수의 근거</strong>와{" "}
        <strong className="text-gc-ink">추천 이유 한 줄</strong>, 제안요청서를 읽어
        정리한 <strong className="text-gc-ink">과업·자격·일정 요약</strong>이 나옵니다.
      </p>

      <div className="mt-8 border border-gc-rule bg-gc-sheet rounded-[3px]">
        {/* 컬럼 머리 */}
        <div
          aria-hidden
          className="hidden sm:grid grid-cols-[48px_minmax(0,1fr)_84px_110px_88px] gap-x-4 px-4 pt-3 pb-2 border-b-2 border-gc-ink text-[11.5px] font-bold text-gc-ink-2"
        >
          <span className="text-right pr-1">순번</span>
          <span>공고</span>
          <span className="text-right">마감</span>
          <span className="text-right">추정가</span>
          <span className="text-right">적합</span>
        </div>

        {/* 개봉된 행 */}
        <div className="grid items-baseline gap-x-4 px-4 py-4 grid-cols-[40px_minmax(0,1fr)] sm:grid-cols-[48px_minmax(0,1fr)_84px_110px_88px]">
          <span className="text-right pr-1 text-[15px] font-bold tabular tabular-nums text-gc-ink-2">
            01
          </span>
          <span className="min-w-0">
            <span className="block text-[15.5px] sm:text-[16.5px] font-bold leading-[1.45] text-gc-ink break-keep">
              청사 냉난방 설비 유지관리 용역
            </span>
            <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px] text-gc-ink-3">
              <span className="font-semibold text-gc-ink-2">○○시 시설관리공단</span>
              <span className="border border-gc-rule rounded-[3px] px-1.5 py-px text-[11.5px] font-semibold text-gc-ink-2 bg-gc-sheet">
                용역
              </span>
              <span>경기</span>
              <span className="sm:hidden tabular tabular-nums font-bold text-gc-ink">
                D-9 · 1.2억 · 적합 72
              </span>
            </span>
          </span>
          <span className="hidden sm:block text-right text-[14px] font-bold tabular tabular-nums text-gc-ink self-start">
            D-9
          </span>
          <span className="hidden sm:block text-right text-[14px] font-semibold tabular tabular-nums text-gc-ink self-start">
            1.2억
          </span>
          <span className="hidden sm:block text-right text-[14px] font-black tabular tabular-nums text-gc-ink self-start">
            72
          </span>
        </div>

        {/* 개봉면 — 절취선 아래 근거 */}
        <div className="border-t border-dashed border-gc-tint-line px-4 sm:pl-[calc(48px+16px+16px)] py-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div>
            <div className="text-[11.5px] font-bold text-gc-ink-2">점수 근거</div>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {SAMPLE_SIGNALS.map((s) => (
                <li
                  key={s.label}
                  className="inline-flex items-baseline gap-1.5 bg-gc-tint text-gc-tint-ink rounded-[3px] px-2 py-1 text-[12.5px] font-semibold"
                >
                  {s.label}
                  <span className="tabular tabular-nums text-[11.5px]">{s.pts}</span>
                </li>
              ))}
            </ul>
            <div className="mt-4 text-[11.5px] font-bold text-gc-ink-2">추천 이유</div>
            <p className="mt-1.5 text-[14px] leading-[1.75] text-gc-ink break-keep">
              과거 거래 기관 ‘○○시 시설관리공단’의 후속 사업이고, 회사 소재지
              경기와 참가가능 지역이 일치한다. 회사 평균 수주 1.4억 대비 사업 규모도
              맞물린다.
            </p>
          </div>
          <div>
            <div className="text-[11.5px] font-bold text-gc-ink-2">문서 요약 · 제안요청서 기준</div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[13.5px] leading-[1.6]">
              <dt className="font-bold text-gc-ink-3">과업</dt>
              <dd className="text-gc-ink break-keep">청사 3개동 냉난방 설비 정기점검·부품 교체·비상 출동. 월 2회 정기점검.</dd>
              <dt className="font-bold text-gc-ink-3">필수</dt>
              <dd className="text-gc-ink break-keep">기계설비유지관리자 선임 · 본사 소재지 경기 · 중소기업 확인서</dd>
              <dt className="font-bold text-gc-ink-3">평가</dt>
              <dd className="text-gc-ink">적격심사 · 최저가</dd>
              <dt className="font-bold text-gc-ink-3">기간</dt>
              <dd className="text-gc-ink">계약일 ~ 12개월</dd>
            </dl>
          </div>
        </div>
      </div>

      <p className="mt-4 text-[13px] text-gc-ink-3 break-keep">
        키워드로도 볼 수 있습니다 — “교량 점검”, “급식 식자재”처럼 관심 영역을 넣으면
        회사 정보 없이 의미가 가까운 공고를 찾습니다. 영업 탐색이나 시장 조사에 맞습니다.
      </p>
    </Wrap>
  );
}

/* ── 어떻게 동작합니다 — 순서가 곧 정보인 4행 ───────────────── */

const STEPS = [
  {
    title: "회사를 읽습니다",
    body: "조달업체 등록정보에서 등록업종·공급물품을, 계약·개찰 데이터에서 수주 이력을 가져옵니다. 회사가 직접 입력할 것은 없습니다.",
    src: ["등록업종·공급물품", "계약·낙찰 이력", "소재지"],
  },
  {
    title: "의미가 가까운 공고를 모읍니다",
    body: "회사와 공고를 각각 벡터로 만들어 비교합니다. 같은 단어가 없어도 “공간정보 구축”과 “GIS 시스템 개발”처럼 뜻이 가까우면 후보가 됩니다.",
    src: ["진행 중 공고 전량"],
  },
  {
    title: "자격과 검토 가치를 봅니다",
    body: "면허·지역 제한에 맞지 않으면 제외합니다. 과거 거래 기관, 비슷한 회사들이 수주한 기관, 사업 규모, 마감까지 남은 날을 점수로 더합니다.",
    src: ["면허·지역 제한", "비슷한 회사의 수주", "추정가"],
  },
  {
    title: "이유를 한 줄로 적습니다",
    body: "점수만 보여주지 않습니다. 어떤 근거가 맞물렸는지 문장으로 적고, 제안요청서가 있으면 과업·자격·일정을 함께 정리합니다.",
    src: ["첨부 제안요청서", "점수 근거"],
  },
];

function Process() {
  return (
    <Wrap>
      <SectionHead title="어떻게 동작합니다" note="회사명 입력에서 결과까지, 순서대로" />
      <ol className="mt-2">
        {STEPS.map((s, i) => (
          <li
            key={s.title}
            className="grid gap-x-5 gap-y-2 py-6 border-b border-gc-rule grid-cols-[40px_minmax(0,1fr)] sm:grid-cols-[48px_minmax(0,1fr)_240px]"
          >
            <span className="text-right pr-1 font-gc-serif font-black text-[22px] leading-none tabular tabular-nums text-gc-ink-2 pt-0.5">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0">
              <h3 className="text-[16.5px] font-bold text-gc-ink break-keep">{s.title}</h3>
              <p className="mt-1.5 max-w-[620px] text-[14.5px] leading-[1.75] text-gc-ink-2 break-keep">
                {s.body}
              </p>
            </div>
            <div className="col-start-2 sm:col-start-3">
              <div className="text-[11.5px] font-bold text-gc-ink-3">쓰는 데이터</div>
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {s.src.map((t) => (
                  <li
                    key={t}
                    className="border border-gc-rule bg-gc-sheet rounded-[3px] px-2 py-0.5 text-[12px] font-semibold text-gc-ink-2"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          </li>
        ))}
      </ol>
    </Wrap>
  );
}

/* ── 키워드 알림과 다른 점 — 대조표 ─────────────────────── */

const COMPARE = [
  ["찾는 방식", "등록한 단어가 제목에 있을 때", "회사 영역과 뜻이 가까울 때 — 단어가 달라도"],
  ["회사를 아는 정도", "키워드 목록", "등록업종·공급물품 + 실제 수주 이력"],
  ["자격 조건", "직접 확인", "면허·지역 제한을 먼저 대조해 제외"],
  ["왜 이 공고인지", "없음", "점수 근거와 이유 한 줄"],
  ["제안요청서", "직접 내려받아 읽기", "첨부 원클릭 + 과업·자격·일정 요약"],
  ["공고가 바뀌면", "새 알림", "정정 차수와 무엇이 바뀌었는지 비교"],
];

function Comparison() {
  return (
    <Wrap>
      <SectionHead title="키워드 알림과 다른 점" />
      {/* 모바일: 핵심 열이 가로 스크롤 뒤로 숨지 않도록 행으로 쌓는다 */}
      <ul className="sm:hidden mt-2">
        {COMPARE.map(([k, a, b]) => (
          <li key={k} className="py-4 border-b border-gc-rule">
            <div className="text-[12px] font-bold text-gc-ink-2">{k}</div>
            <div className="mt-1.5 grid grid-cols-[64px_minmax(0,1fr)] gap-x-3 gap-y-1 text-[14px]">
              <span className="text-[11.5px] font-bold text-gc-ink-3 pt-0.5">키워드 알림</span>
              <span className="text-gc-ink-3 break-keep">{a}</span>
              <span className="text-[11.5px] font-gc-serif font-black text-gc-ink pt-0.5">조달핏</span>
              <span className="text-gc-ink font-semibold break-keep">{b}</span>
            </div>
          </li>
        ))}
      </ul>
      <div className="hidden sm:block mt-2">
        <table className="w-full border-collapse text-[14px]">
          <thead>
            <tr className="border-b-2 border-gc-ink text-[11.5px] font-bold text-gc-ink-2">
              <th className="text-left py-2.5 pr-4 w-[160px]">항목</th>
              <th className="text-left py-2.5 pr-4 w-[38%]">키워드 알림</th>
              <th className="text-left py-2.5 font-gc-serif font-black text-[13px] text-gc-ink">
                조달핏
              </th>
            </tr>
          </thead>
          <tbody>
            {COMPARE.map(([k, a, b]) => (
              <tr key={k} className="border-b border-gc-rule align-top">
                <th scope="row" className="text-left py-3.5 pr-4 font-bold text-gc-ink-2">
                  {k}
                </th>
                <td className="py-3.5 pr-4 text-gc-ink-3 break-keep">{a}</td>
                <td className="py-3.5 text-gc-ink font-semibold break-keep">{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Wrap>
  );
}

/* ── 데이터 장부 — 출처·갱신 주기 ─────────────────────── */

const SOURCES: [string, string, string][] = [
  ["입찰공고 · 첨부파일", "입찰공고정보 · 공공데이터개방표준", "매시간"],
  ["제안요청서 본문 · AI 요약", "첨부파일 원문에서 추출", "매시간"],
  ["계약 · 낙찰 · 개찰 참가", "계약정보 · 낙찰정보", "매일 새벽"],
  ["회사 등록정보 · 업종 · 공급물품", "조달업체정보", "매일 새벽"],
  ["면허 · 지역 제한", "입찰공고정보", "매일 새벽"],
  ["사전규격 · 의견 · 발주계획", "사전규격정보 · 발주계획정보", "매일 새벽"],
  ["부정당 제재", "조달업체정보", "매일 새벽"],
];

function Ledger({ stats }: { stats: AboutStats }) {
  return (
    <Wrap>
      <SectionHead
        title="데이터 출처"
        note={`조달청 나라장터(G2B) 공공데이터포털 OpenAPI · 누적 공고 ${n(stats.totalNotices)}건`}
      />
      <p className="mt-5 max-w-[720px] text-[15px] leading-[1.8] text-gc-ink-2 break-keep">
        전부{" "}
        <a
          href="https://www.data.go.kr"
          target="_blank"
          rel="noreferrer"
          className="font-bold text-gc-ink underline underline-offset-4 decoration-gc-tint-line hover:decoration-gc-ink"
        >
          공공데이터포털
        </a>
        이 공개하는 공식 API입니다. 회사가 나라장터에 등록한 정보가 원본이라, 회사가
        그쪽에서 고치면 다음 갱신 때 조달핏에도 반영됩니다. 첨부파일 원본은 저장하지
        않고 추출한 텍스트만 보관하며, 원문 링크를 항상 함께 둡니다.
      </p>
      <div className="mt-6">
        <table className="w-full border-collapse text-[14px]">
          <thead>
            <tr className="border-b-2 border-gc-ink text-[11.5px] font-bold text-gc-ink-2">
              <th className="text-left py-2.5 pr-4">데이터</th>
              <th className="text-left py-2.5 pr-4 hidden sm:table-cell">API 서비스</th>
              <th className="text-right py-2.5 w-[84px]">갱신</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map(([d, s, c]) => (
              <tr key={d} className="border-b border-gc-rule">
                <td className="py-3 pr-4 font-semibold text-gc-ink break-keep">
                  {d}
                  <span className="sm:hidden block mt-0.5 text-[12px] font-normal text-gc-ink-3">{s}</span>
                </td>
                <td className="py-3 pr-4 text-gc-ink-3 break-keep hidden sm:table-cell">{s}</td>
                <td className="py-3 text-right font-bold tabular tabular-nums text-gc-ink-2 whitespace-nowrap">
                  {c}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Wrap>
  );
}

/* ── 할 수 없는 것 — 정직한 디스커버리 ─────────────────── */

const LIMITS = [
  ["낙찰을 보장하지 않습니다", "매칭 점수는 “검토할 가치”의 신호이지 “이길 가능성”이 아닙니다. 그래서 낙찰 확률 같은 숫자는 어디에도 쓰지 않습니다."],
  ["자격 판정은 보조 신호입니다", "면허·지역 제한은 공개 데이터로 대조하지만, 최종 입찰 가능 여부는 공고 원문과 회사 자격으로 직접 확인해야 합니다."],
  ["AI 요약은 원문을 대신하지 않습니다", "제안요청서 요약은 문서에 적힌 내용만 옮기지만 읽기 오류가 있을 수 있습니다. 요약 옆에 원문 링크를 항상 둡니다."],
  ["회사 데이터가 적으면 정확도가 낮습니다", "등록업종·공급물품이 없거나 수주 이력이 없는 회사는 키워드 검색으로 전환을 안내합니다."],
];

function Limits() {
  return (
    <Wrap>
      <SectionHead title="할 수 없는 것, 보장하지 않는 것" note="최종 판단은 사람이 합니다" />
      <ul className="mt-2">
        {LIMITS.map(([t, b]) => (
          <li
            key={t}
            className="grid gap-x-6 gap-y-1 py-5 border-b border-gc-rule sm:grid-cols-[300px_minmax(0,1fr)]"
          >
            <h3 className="text-[15.5px] font-bold text-gc-ink break-keep">{t}</h3>
            <p className="text-[14.5px] leading-[1.75] text-gc-ink-2 break-keep">{b}</p>
          </li>
        ))}
      </ul>
    </Wrap>
  );
}

/* ── 연락처 + 다음 행동 ─────────────────────────────── */

function Contact() {
  return (
    <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-14 sm:pt-16 pb-16 sm:pb-20">
      <div className="gc-double-rule pt-6 flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div>
          <h2 className="font-gc-serif font-black text-[22px] sm:text-[26px] tracking-[-0.02em] text-gc-ink break-keep">
            회원가입 없이 바로 확인할 수 있습니다
          </h2>
          <p className="mt-2 text-[14.5px] text-gc-ink-2 break-keep">
            문의·제안·오류 제보:{" "}
            <a
              href="mailto:jsw7980@gmail.com"
              className="font-bold text-gc-ink underline underline-offset-4 decoration-gc-tint-line hover:decoration-gc-ink"
            >
              jsw7980@gmail.com
            </a>
          </p>
        </div>
        <Link
          href="/#gc-search"
          className="inline-flex items-center justify-center h-11 px-5 bg-gc-band text-gc-band-hi text-[14px] font-bold rounded-[3px] hover:bg-gc-ink transition-colors whitespace-nowrap"
        >
          우리 회사 공고 보기 →
        </Link>
      </div>
      <p className="mt-6 text-[12.5px] text-gc-ink-3">
        © {new Date().getFullYear()} 조달핏. 데이터는 공공데이터포털 이용 조건을 따릅니다.
      </p>
    </section>
  );
}
