// frontend/src/app/(renewal)/companies/[bizrno]/page.tsx
// 회사 페이지(06) — /companies/[bizrno] 본문을 리뉴얼 디자인으로.
//
// URL·메타·JSON-LD·noindex 규칙은 옛 페이지에서 **그대로 가져온다**. SEO 비중이 큰 화면이고
// 그 규칙들은 각각 이유가 있다(비공개 요청 0037, 깡통·폐업 색인 제외, 제목에 숫자 비노출 2026-09-22).
//
// 머리 장면(캔버스)은 없다 — 2026-10-17 결정: 회사 페이지는 SSR 문서이고 추천은 대부분 캐시
// 히트라 "계산이 안 걸리면 안 보여준다" 원칙상 캔버스가 설 자리가 없다. 걸러낸 경로는 숫자 한 줄.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AwardsPanel, ContractsPanel, Panel, PeersPanel } from "@/components/company/CompanyPanels";
import { JsonLd } from "@/components/JsonLd";
import { ResultRows } from "@/components/results/ResultRows";
import { StarCompany } from "@/components/StarCompany";
import { getRecommendations } from "@/lib/api";
import { getSessionUser } from "@/lib/auth";
import {
  BROWSE_SIDO_LIST,
  fetchCompanyAwards,
  fetchCompanyByBizrno,
  fetchCompanyContracts,
  fetchCompanyProfile,
  fetchSimilarNoticeAwardees,
  summarizeAwards,
  summarizeContracts,
} from "@/lib/company";
import { companyBreadcrumbJsonLd, companyOrganizationJsonLd } from "@/lib/jsonld";
import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";
import { maskBizrno } from "@/lib/utils";

// 정적 생성을 하지 않는다. 리뉴얼 레이아웃의 nav 가 로그인 상태를 읽어 쿠키를 쓰기 때문에
// 빌드 때 미리 만들 수 없다 — generateStaticParams 를 두면 운영에서 DYNAMIC_SERVER_USAGE 로 500 이 난다
// (2026-10-23 배포 직후 확인). ISR 비용 이점은 포기한다.

type Props = { params: Promise<{ bizrno: string }> };

const nf = new Intl.NumberFormat("ko-KR");

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bizrno } = await params;
  const normalized = bizrno.replace(/\D/g, "");
  const company = await fetchCompanyByBizrno(normalized);
  // 비공개 요청 회사는 존재하지 않는 것처럼 다룬다 (0037). 메타까지 막아야 상호가 새어나가지 않는다.
  if (!company || company.optout_at) return { title: "회사 정보 없음 | 조달핏", robots: { index: false } };

  const awards = await fetchCompanyAwards(normalized, 50);
  const hasHistory = summarizeAwards(awards).count >= 1 || company.contract_count >= 1;
  // 제목·설명에 수주 건수와 평균 투찰률은 넣지 않는다 (2026-09-22) — 검색 결과에 숫자가 뜨면
  // 상호 검색만으로 수주 현황이 보이고, 평균 투찰률은 경쟁사에게 가격 전략을 알려준다.
  const title = hasHistory
    ? `${company.corp_nm} 나라장터 수주 이력 | 조달핏`
    : `${company.corp_nm} 등록업종·공공조달 정보 | 조달핏`;
  const desc = hasHistory
    ? `${company.corp_nm}의 나라장터 수주 이력과 등록업종·공급물품을 정리했습니다. 이 회사에 맞는 신규 공고도 함께 보여드립니다. 매일 갱신.`
    : `${company.corp_nm}의 등록업종·공급물품 기반으로 적합한 신규 나라장터 공고를 추천합니다. 매일 갱신.`;
  // 추천 벡터도 수주 이력도 없는 깡통 페이지와 폐업 회사는 색인 제외
  const isThin = !company.has_embedding && company.contract_count === 0;
  const isClosed = company.biz_status_cd === "03";
  return {
    title,
    description: desc,
    alternates: { canonical: `/companies/${normalized}` },
    robots: isThin || isClosed ? { index: false, follow: true } : undefined,
    openGraph: { siteName: "조달핏", title, description: desc, type: "profile", locale: "ko_KR" },
    keywords: [company.corp_nm, `${company.corp_nm} 입찰`, `${company.corp_nm} 공고`, `${company.corp_nm} 수주`, "공공조달", "나라장터"],
  };
}

export default async function CompanyPage({ params }: Props) {
  const { bizrno } = await params;
  const normalized = bizrno.replace(/\D/g, "");
  if (normalized.length !== 10) notFound();
  const company = await fetchCompanyByBizrno(normalized);
  if (!company) notFound();
  if (company.optout_at) notFound(); // 비공개 요청 (0037) — 스트리밍 전에 던져야 실제 404 가 나간다

  const closed = company.biz_status_cd === "03";
  const [profile, contracts, awards, peers] = await Promise.all([
    fetchCompanyProfile(company.bizrno).catch(() => null),
    fetchCompanyContracts(normalized, 30).catch(() => []),
    fetchCompanyAwards(normalized, 50).catch(() => []),
    fetchSimilarNoticeAwardees(normalized).catch(() => []),
  ]);
  const awardSummary = summarizeAwards(awards);
  const sectors = summarizeContracts(contracts);
  // 브레드크럼의 시·도 칸은 지역별 목록 페이지가 있는 이름만 (rgn_nm 첫 토큰, 개편 전 이름은 그대로 — 목록도 like 로 같은 기준)
  const sidoToken = (company.rgn_nm || "").split(" ")[0];
  const sido = (BROWSE_SIDO_LIST as readonly string[]).includes(sidoToken) ? sidoToken : null;

  return (
    <div className="pb-20">
      <JsonLd data={[
        companyOrganizationJsonLd({ bizrnoNorm: normalized, corpNm: company.corp_nm, rgnNm: company.rgn_nm }),
        companyBreadcrumbJsonLd({ bizrnoNorm: normalized, corpNm: company.corp_nm, sido }),
      ]} />

      <header className="mt-8 border-b border-ink pb-3.5 max-sm:mt-5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="text-[30px] font-[650] tracking-[-0.03em] text-ink max-sm:text-[22px]">{company.corp_nm}</h1>
          <span className="num text-[13px] text-ink-mute">{maskBizrno(company.bizrno)}</span>
          <Suspense fallback={null}><CompanyStar bizrnoNorm={normalized} /></Suspense>
          {closed && <span className="rounded-full border border-field px-2 py-0.5 text-[12px] text-ink-mute">국세청 기준 폐업</span>}
        </div>
        <p className="mt-1.5 text-[13.5px] text-ink-g">
          {company.rgn_nm || "지역 미상"}
          {profile && (
            <>
              {" · "}등록업종 {profile.industries.length} · 공급물품 {profile.products.length}
            </>
          )}
          {company.contract_count > 0 && <> · 계약 {nf.format(company.contract_count)}건</>}
        </p>
        <CompanySummary corpNm={company.corp_nm} rgn={company.rgn_nm} profile={profile} closed={closed} recommends={company.has_embedding} />
      </header>

      {/* 판 1 — 검토할 공고. 폐업이면 추천하지 않는다(낼 수 없는 회사에게 공고를 권하지 않는다). */}
      {closed ? (
        <Panel title="검토할 공고">
          <p className="mt-3 text-[14px] leading-[1.75] text-ink-g">
            국세청 기준 폐업 회사라 추천을 하지 않습니다. 사업자 상태가 바뀌면 다시 보입니다.
          </p>
        </Panel>
      ) : (
        <Suspense
          fallback={
            <Panel title="검토할 공고">
              <p className="mt-3 text-[14px] text-ink-g">계산 중입니다.</p>
            </Panel>
          }
        >
          <RecoPanel bizrnoNorm={normalized} corpNm={company.corp_nm} hasEmbedding={company.has_embedding} />
        </Suspense>
      )}

      <ContractsPanel rows={contracts} topInstt={sectors.top_institutions} />
      <AwardsPanel rows={awards} summary={awardSummary} />
      <PeersPanel peers={peers} />

      {!closed && contracts.length === 0 && awards.length === 0 && (
        <p className="mt-5 text-[13px] leading-[1.7] text-ink-mute">
          나라장터에 수집된 계약·낙찰 기록이 없습니다. 기록이 생기면 이 자리에 쌓입니다.
        </p>
      )}
    </div>
  );
}

/** 요약 한 문단 — 검색엔진·AI 답변이 그대로 인용할 수 있는 사실 문장(GEO, 2026-10-24).
 *  수주 건수·투찰률은 넣지 않는다: 제목·설명에서 뺀 이유(2026-09-22, 상호 검색만으로 수주 현황·가격 전략이
 *  드러남)가 인용 문장에도 똑같이 적용된다. 등록정보와 서비스가 하는 일만. */
function CompanySummary({ corpNm, rgn, profile, closed, recommends }: {
  corpNm: string; rgn: string | null; profile: Awaited<ReturnType<typeof fetchCompanyProfile>> | null; closed: boolean; recommends: boolean;
}) {
  const rep = profile?.industryLinks.find((l) => l.rep)?.nm ?? profile?.industries[0] ?? null;
  // 조사는 마지막 한글 글자의 받침으로 — "한종산업개발(주)는" 처럼 괄호 뒤가 아니라 그 앞 글자를 본다
  const last = [...corpNm].reverse().find((ch) => ch >= "가" && ch <= "힣");
  const josa = last ? ((last.charCodeAt(0) - 0xac00) % 28 ? "은" : "는") : "은(는)";
  // 0 개는 "0개가 등록된" 대신 없다고 말한다
  const ind = profile?.industries.length ? `등록업종 ${profile.industries.length}개${rep ? `(대표 ${rep})` : ""}` : null;
  const prd = profile?.products.length ? `공급물품 ${profile.products.length}개` : null;
  const reg = ind && prd ? `나라장터에 ${ind}와 ${prd}가 등록된 사업자입니다.`
    : ind ? `나라장터에 ${ind}이 등록된 사업자입니다(공급물품 미등록).`
    : prd ? `나라장터에 ${prd}가 등록된 사업자입니다(등록업종 미등록).`
    : "나라장터에 등록업종·공급물품 정보가 없는 사업자입니다.";
  return (
    <p className="mt-2.5 max-w-[760px] text-[13.5px] leading-[1.7] text-ink-g">
      {corpNm}{josa} {rgn ? `${rgn} 소재, ` : ""}{reg}{" "}
      {closed
        ? "국세청 기준 폐업 상태라 공고를 추천하지 않습니다."
        : recommends
          ? "조달핏은 이 등록정보와 나라장터 수주 이력을 함께 분석해 지금 입찰 가능한 공고 중 이 회사가 검토할 만한 공고를 매일 추립니다."
          : "추천 기준이 될 등록정보·수주 이력이 없어 업종·품목 키워드로 공고를 찾을 수 있습니다."}{" "}
      나라장터 공공데이터 기반 · 매일 갱신.
    </p>
  );
}

async function CompanyStar({ bizrnoNorm }: { bizrnoNorm: string }) {
  const user = await getSessionUser();
  const saved = user ? await getSavedCompanyKeys() : new Set<string>();
  return <StarCompany bizrnoNorm={bizrnoNorm} saved={saved.has(bizrnoNorm)} loggedIn={!!user} />;
}

/** 추천 판 — 비스트림 경로(캐시 read-through). 머리 장면 없이 걸러낸 경로 한 줄만. */
async function RecoPanel({ bizrnoNorm, corpNm, hasEmbedding }: { bizrnoNorm: string; corpNm: string; hasEmbedding: boolean }) {
  if (!hasEmbedding) {
    return (
      <Panel title="검토할 공고">
        <p className="mt-3 text-[14px] leading-[1.75] text-ink-g">
          나라장터 업체정보에 등록업종·공급물품이 없고 수주 이력도 없어 참가 자격과 적합도를 판정할 기준이 없습니다. 업종이나 품목을 글로
          적어 찾는 방법은{" "}
          <a href={`/recommendations?q=${encodeURIComponent(corpNm)}`} className="border-b border-field text-ink hover:border-orange">
            여기
          </a>
          에서 됩니다.
        </p>
      </Panel>
    );
  }
  const [d, user] = await Promise.all([
    getRecommendations({ query: bizrnoNorm, mode: "company", limit: 20, candidate_pool: 200, with_explanation: false }).catch(() => null),
    getSessionUser(),
  ]);
  if (!d || d.error) {
    return (
      <Panel title="검토할 공고">
        <p role="alert" className="mt-3 text-[14px] leading-[1.75] text-ink-g">추천 결과를 불러오지 못했습니다.</p>
        <a href={`/recommendations?company=${bizrnoNorm}`} className="mt-3 inline-block border-b border-field text-[13px] text-ink hover:border-orange">다시 시도</a>
      </Panel>
    );
  }
  const results = d.results;
  const reviewed = user ? await getReviewedKeys().catch(() => new Set<string>()) : new Set<string>();
  const f = d?.funnel ?? null;

  return (
    <Panel
      title={`검토할 공고 ${results.length}건`}
      meta={
        f ? (
          <>
            걸러낸 경로 <b className="num font-[650] text-ink">{nf.format(f.total)}</b> → 비슷한 순서로 추린 공고 200 → 검토할 공고{" "}
            <b className="num font-[650] text-orange-ink">{results.length}</b>
          </>
        ) : (
          "적합 순"
        )
      }
    >
      {results.length === 0 ? (
        <p className="mt-3 text-[14px] leading-[1.75] text-ink-g">
          현재 추천 기준으로 검토할 공고가 없습니다. 업종이나 품목으로도 검색할 수 있습니다.
        </p>
      ) : (
        <div className="mt-1">
          <ResultRows
            results={results}
            loggedIn={!!user}
            reviewed={reviewed}
            viaBizrno={bizrnoNorm}
            next={`/companies/${bizrnoNorm}`}
            today={new Date()}
            keywordMode={false}
          />
        </div>
      )}
    </Panel>
  );
}
