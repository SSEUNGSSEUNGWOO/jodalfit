// frontend/src/app/(renewal)/admin/page.tsx
// 관리 — 읽기 전용 운영 숫자. 관리자(ADMIN_EMAILS)만. 아니면 403 이 아니라 404 — 경로의 존재를 알리지 않는다.
// robots.txt 에 관리 경로를 노출하지 않는다. noindex 메타. nav 링크 없음 — 관리자가 직접 접근한다.
// 쓰기 동작(사용자 삭제·비밀번호 초기화·공고 비공개)은 두지 않는다 — Supabase 대시보드가 맡는다(2026-10-26 결정).
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHead } from "@/components/PageHead";
import { Panel, PanelHead } from "@/components/Panel";
import { fetchAdminData, isAdmin, type Funnel, type Health } from "@/lib/admin";
import { getSessionUser } from "@/lib/auth";
import { OverviewPanel } from "@/components/admin/OverviewPanel";
import { InterestPanel } from "@/components/admin/InterestPanel";
import { ConversionPanel } from "@/components/admin/ConversionPanel";
import { PagedTable } from "./PagedTable";

export const metadata: Metadata = { title: "관리 | 조달핏", robots: { index: false, follow: false } };

const nf = new Intl.NumberFormat("ko-KR");
const tf = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
const t = (s: string | null | undefined) => (s ? tf.format(new Date(s)).replace(/\. /g, ".").replace(/\.$/, "") : "—");
const md = (ymd: string) => `${ymd.slice(5, 7)}.${ymd.slice(8, 10)}`;
const pct = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(v * 100 >= 10 ? 0 : 1)}%`);
const ms = (v: number | null) => (v == null ? "—" : `${nf.format(v)} ms`);

const FUNNEL: { k: keyof Funnel; label: string; h: string }[] = [
  { k: "searches", label: "사람 검색", h: "내부 SSR·봇 제외" },
  { k: "visitors", label: "검색 IP", h: "IP 해시 수 · 사람 수 아님" },
  { k: "identified", label: "회사 식별", h: "회사 모드 중 매칭" },
  { k: "clicks", label: "공고 클릭", h: "결과·회사 페이지" },
  { k: "signups", label: "가입 계정", h: "인증 전 포함 · 관리자·테스트 제외" },
  { k: "saved", label: "회사 저장", h: "☆" },
  { k: "reviewed", label: "공고 저장", h: "현재 보관된 공고" },
];
const HEALTH: { k: keyof Health; label: string; f: (v: number | null) => string; h: string }[] = [
  { k: "errorRate", label: "검색 문제 비율", f: pct, h: "회사 못 찾음·등록정보 없음 포함 — 서버 오류 아님" },
  { k: "zeroRate", label: "결과 0건 비율", f: pct, h: "오류 아닌데 0건" },
  { k: "p50", label: "p50 응답", f: ms, h: "추천 API latency_ms" },
  { k: "helpful", label: "도움이 됐다", f: pct, h: "결과 화면 '도움이 됐습니까' 예 비율 (0063)" },
  { k: "helpfulN", label: "응답 수", f: (v) => (v == null ? "—" : String(v)), h: "예·아니오 합" },
];
const KIND_LABEL = { idea: "의견", question: "문의", bug: "오류 제보" } as const;
const TYPE_LABEL: Record<string, string> = { home: "홈", company: "회사 페이지", companies: "회사 목록", notice: "공고 페이지", notices: "공고 목록", results: "추천 결과", saved: "검토함", auth: "로그인·가입", other: "그 밖" };

export default async function AdminPage() {
  const user = await getSessionUser();
  if (!user || !isAdmin(user.email)) notFound();
  const d = await fetchAdminData();
  const v = d.visits;
  const vToday = v.daily.find((x) => x.date === d.todayKst);
  const weekViews = v.daily.reduce((sum, row) => sum + row.views, 0);

  return (
    <>
      <PageHead title="관리" small="서비스 현황" meta={[`${d.todayKst} 한국 시간 기준`, "읽기 전용 · 방문과 실제 사용을 함께 확인"]} />

      <OverviewPanel data={d.overview} />
      <InterestPanel data={d.interest} />

      <details id="admin-problems" data-admin-problems className="mt-[14px] scroll-mt-6 rounded-[12px] border border-hair bg-panel px-5 py-4">
        <summary className="cursor-pointer text-[14px] font-semibold text-ink">문제가 기록된 검색 보기 · 최근 완료 7일 · 최신 30건</summary>
        <Table head={["시각", "검색어", "모드", "기록된 문제"]}
          rows={d.problemQueries.map((r) => [t(r.at), r.query, r.mode, `${r.errorMsg ?? "상세 사유 없음"}${r.fallback ? " · 키워드 결과로 이어짐" : ""}`])}
          empty={d.overview.searchesAvailable ? "이 기간에 기록된 검색 문제가 없습니다." : "검색 기록을 모두 읽지 못했습니다."} />
      </details>

      <details id="admin-details" data-admin-details className="mt-6">
        <summary className="cursor-pointer rounded-[8px] border border-field px-4 py-3 text-[14px] font-semibold text-ink">상세 기록 보기 — 오늘 활동·전환·방문 경로·회원·검색·문의</summary>

      <Panel className="mt-[22px]" data-admin="funnel">
        <PanelHead title="활동 건수" small="오늘 진행 중 / 오늘 포함 7일" summary={[<span key="w">각 항목은 별도 집계이며 같은 사용자의 전환 단계가 아닙니다</span>]} />
        <dl className="m-0 grid grid-cols-7 gap-x-5 gap-y-5 pt-5 max-sm:grid-cols-2">
          {FUNNEL.map((f) => (
            <div key={f.k}>
              <dt className="t-k">{f.label}</dt>
              <dd className="m-0 mt-1 flex items-baseline gap-1.5 text-ink">
                <span className="num text-[26px] font-semibold leading-none tracking-[-0.03em]">{nf.format(d.today[f.k])}</span>
                <span className="num text-[13px] text-ink-g">/ {nf.format(d.week[f.k])}</span>
              </dd>
              <dd className="m-0 mt-1 text-[12px] text-ink-mute">{f.h}</dd>
            </div>
          ))}
        </dl>
        <div data-admin-daily className="mt-6">
          <Table
            head={["날짜", ...FUNNEL.map((f) => f.label)]}
            rows={d.daily.map((r) => [md(r.date), ...FUNNEL.map((f) => nf.format(r[f.k]))])}
            empty=""
            numeric
          />
        </div>
      </Panel>

      <ConversionPanel data={d.conversions} />

      <Panel className="mt-[14px]" data-admin="visits">
        <PanelHead title="방문" small="브라우저 계측 · 오늘 포함 7일" summary={v.error ? undefined : [
          <span key="t">오늘 페이지뷰 <b>{nf.format(vToday?.views ?? 0)}</b> · 방문자 <b>{nf.format(vToday?.visitors ?? 0)}</b></span>,
          <span key="w">7일 페이지뷰 {nf.format(weekViews)}회 · 일별 방문자는 합산하지 않습니다</span>,
        ]} />
        {v.error ? (
          <p className="m-0 pt-5 text-[14px] text-ink-mute">방문 숫자를 못 읽었습니다 — {v.error}. 활동 건수의 &lsquo;검색 IP&rsquo;는 검색 로그 기준이라 페이지만 보고 나간 사람은 세지 않습니다.</p>
        ) : (
          <div className="grid grid-cols-3 gap-6 max-sm:grid-cols-1">
            <Table head={["날짜", "페이지뷰", "방문자"]} rows={v.daily.map((r) => [md(r.date), nf.format(r.views), nf.format(r.visitors)])} empty="7일 페이지뷰가 없습니다." numeric />
            <Table head={["페이지", "페이지뷰", "방문자"]} rows={v.byType.map((r) => [TYPE_LABEL[r.type] ?? r.type, nf.format(r.views), nf.format(r.visitors)])} empty="—" numeric />
            <Table head={["유입", "페이지뷰", "방문자"]} rows={v.referrers.map((r) => [r.domain === "$direct" ? "직접·북마크" : r.domain, nf.format(r.views), nf.format(r.visitors)])} empty="—" numeric />
          </div>
        )}
      </Panel>

      <div className="mt-[14px] grid grid-cols-[1fr_1.4fr] gap-[14px] max-sm:grid-cols-1">
        <Panel data-admin="health">
          <PanelHead title="응답 건강" summary={[<span key="w">오늘 / 7일</span>]} />
          <dl className="m-0 grid grid-cols-3 gap-x-5 gap-y-5 pt-5 max-sm:grid-cols-1">
            {HEALTH.map((h) => (
              <div key={h.k}>
                <dt className="t-k">{h.label}</dt>
                <dd className="m-0 mt-1 flex flex-wrap items-baseline gap-x-1.5 text-ink">
                  <span className="num text-[22px] font-semibold leading-none tracking-[-0.03em]">{h.f(d.health.today[h.k])}</span>
                  <span className="num text-[13px] text-ink-g">/ {h.f(d.health.week[h.k])}</span>
                </dd>
                <dd className="m-0 mt-1 text-[12px] text-ink-mute">{h.h}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel data-admin="zero">
          <PanelHead title="의미 유사 추천 0건 검색" small="최근 7일 · 최대 50" summary={[<span key="n">글자 일치 검색 결과는 별도이므로 공고 전체가 0건이라는 뜻은 아닙니다</span>]} />
          <Table
            head={["시각", "모드", "질의", "매칭 회사"]}
            rows={d.zeroQueries.map((s) => [t(s.at), s.mode, s.query, s.matchedBizrno ? <Link key="m" href={`/companies/${s.matchedBizrno}`} className="u-link">{s.matched ?? s.matchedBizrno}</Link> : (s.matched ?? "—")])}
            empty="최근 7일 결과 0건 질의가 없습니다."
          />
        </Panel>
      </div>

      <Panel className="mt-[14px]" data-admin="feedback">
        <PanelHead title="의견·문의" small="최근 50 · /feedback" summary={[<span key="n">답장은 적힌 이메일로 직접 · 처리 표시는 Supabase feedback.handled_at</span>]} />
        <Table
          head={["시각", "종류", "내용", "답장 주소", "보낸 페이지"]}
          rows={d.feedback.map((f) => [
            t(f.at),
            <span key="k" className={f.kind === "bug" ? "text-orange-ink" : undefined}>{KIND_LABEL[f.kind]}</span>,
            <span key="m" className={`whitespace-pre-wrap break-keep ${f.handled ? "text-ink-mute" : ""}`}>{f.message}</span>,
            f.email ? <a key="e" href={`mailto:${f.email}`} className="u-link">{f.email}</a> : "—",
            f.page ? f.page.replace(/^https?:\/\/(www\.)?jodalfit\.co\.kr/, "") : "—",
          ])}
          empty="아직 들어온 의견·문의가 없습니다."
        />
      </Panel>

      <Panel className="mt-[14px]" data-admin="users">
        <PanelHead title="가입자" small={`${d.users.length}계정 · 관리자·테스트 제외`} />
        <Table
          head={["가입", "이메일", "인증", "마지막 로그인", "저장", "검토"]}
          rows={d.users.map((u) => [t(u.createdAt), u.email, u.confirmed ? "완료" : "대기", t(u.lastSignInAt), nf.format(u.saved), nf.format(u.reviewed)])}
          empty="가입자가 없습니다."
        />
      </Panel>

      <Panel className="mt-[14px]" data-admin="searches">
        <PanelHead title="사람 검색" small="최근 7일 · 최신순 · 최대 200 · 25건씩 · 외부 유입은 방문 판" />
        <PagedTable
          head={["시각", "모드", "질의", "매칭 회사", "결과", "IP", "검색한 페이지"]}
          rows={d.searches.map((s) => [
            t(s.at), s.mode, s.query,
            s.matchedBizrno ? <Link key="m" href={`/companies/${s.matchedBizrno}`} className="u-link">{s.matched ?? s.matchedBizrno}</Link> : (s.matched ?? "—"),
            s.error ? <span key="e" className="text-orange-ink">오류</span> : s.results == null ? "—" : nf.format(s.results),
            s.ip || "—", s.referer ?? "—",
          ])}
          empty="최근 7일 사람 검색이 없습니다."
        />
      </Panel>

      <div className="mt-[14px] grid grid-cols-2 gap-[14px] max-sm:grid-cols-1">
        <Panel data-admin="saved">
          <PanelHead title="저장한 회사" small="최근 50" />
          <Table
            head={["시각", "사용자", "회사"]}
            rows={d.savedRows.map((r) => [t(r.at), r.user, <Link key="c" href={`/companies/${r.bizrnoNorm}`} className="u-link">{r.name}</Link>])}
            empty="저장한 회사가 없습니다."
          />
        </Panel>
        <Panel data-admin="reviewed">
          <PanelHead title="검토한 공고" small="최근 50" />
          <Table
            head={["시각", "사용자", "공고"]}
            rows={d.reviewedRows.map((r) => [t(r.at), r.user, <Link key="n" href={`/notices/${r.bidNtceNo}`} className="u-link">{r.title}</Link>])}
            empty="검토한 공고가 없습니다."
          />
        </Panel>
      </div>
      </details>
    </>
  );
}

/** 얇은 표 — 머리 먹 괘선, 행 헤어라인. 390 에서는 가로 스크롤(표 자체를 두 줄로 접지 않는다 — 관리 화면). numeric 이면 첫 열 뒤 전부 오른쪽 정렬. */
function Table({ head, rows, empty, numeric = false }: { head: string[]; rows: React.ReactNode[][]; empty: string; numeric?: boolean }) {
  if (rows.length === 0) return empty ? <p className="m-0 pt-5 text-[14px] text-ink-mute">{empty}</p> : null;
  return (
    <div className="overflow-x-auto pt-2">
      <table className="w-full border-collapse text-[13.5px] leading-[1.5]">
        <thead>
          <tr className="rule-ink text-left text-[12px] font-semibold text-ink-dim">
            {head.map((h, j) => <th key={h} className={`whitespace-nowrap py-2 pr-4 font-semibold ${numeric && j > 0 ? "text-right" : ""}`}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-rule align-top">
              {r.map((c, j) => <td key={j} className={j === 0 ? "num whitespace-nowrap py-2 pr-4 text-ink-g" : `py-2 pr-4 text-ink ${numeric ? "num text-right" : ""}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
