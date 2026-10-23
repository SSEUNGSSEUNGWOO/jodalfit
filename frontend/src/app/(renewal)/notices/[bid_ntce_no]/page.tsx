// frontend/src/app/(renewal)/notices/[bid_ntce_no]/page.tsx
// 공고 상세(07) — /notices/[no] 본문을 리뉴얼 디자인으로.
// URL·메타·JSON-LD·ISR 규칙은 옛 페이지에서 그대로 가져온다(SEO 비중이 큰 화면).
//
// 서버 출력에 '오늘'이 들어가면 안 된다 — 출력이 전과 같아야 Vercel 이 ISR Write 를 안 한다.
// D-day 계산은 클라이언트에서 하고, 서버는 날짜 문자열만 넘긴다.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { NoticeRailClient } from "@/components/notice/NoticeRailClient";
import { InstitutionSection, RequirementsSection, StagesSection, WorkSection } from "@/components/notice/NoticeBody";
import { toLifecycleData } from "@/lib/lifecycle-data";
import { noticeJsonLd } from "@/lib/jsonld";
import { fetchLifecycle } from "@/lib/notice";
import { formatDateKR, formatKRW } from "@/lib/utils";

type Props = { params: Promise<{ bid_ntce_no: string }> };

export const revalidate = 3600;

// 빈 배열이라도 있어야 동적 라우트가 요청마다 SSR 이 아니라 ISR 로 빌드된다.
export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bid_ntce_no } = await params;
  const lifecycle = await fetchLifecycle(bid_ntce_no);
  if (!lifecycle) return { title: "공고 정보 없음 | 조달핏", robots: { index: false } };
  const { notice } = lifecycle;
  const closeRaw = notice.bid_clse_date ? formatDateKR(notice.bid_clse_date) : null;
  const closeLabel = closeRaw && closeRaw !== "—" ? closeRaw : null;
  // 공고명은 나라장터 원문 그대로라 경쟁 사이트와 제목이 글자까지 같아진다 — 마감일을 붙여 구별한다.
  const title = closeLabel ? `${notice.bid_ntce_nm} · ${closeLabel} 마감 | 조달핏` : `${notice.bid_ntce_nm} | 조달핏`;
  const priceRaw = formatKRW(notice.presmpt_prce);
  const priceLabel = priceRaw !== "—" ? `추정 ${priceRaw}` : null;
  const desc = `${[notice.dmnd_instt_nm ?? notice.ntce_instt_nm ?? null, notice.bsns_div_nm, priceLabel, closeLabel ? `마감 ${closeLabel}` : null]
    .filter(Boolean)
    .join(" · ")}. 발주계획부터 낙찰까지 전 과정 분석.`;
  return {
    title,
    description: desc,
    alternates: { canonical: `/notices/${bid_ntce_no}` },
    openGraph: { title: notice.bid_ntce_nm, description: desc, type: "article", locale: "ko_KR" },
    keywords: [notice.bid_ntce_nm, notice.bid_ntce_no, notice.dmnd_instt_nm ?? "", "공공입찰", "나라장터", "공공조달"].filter(Boolean),
  };
}

export default async function NoticePage({ params }: Props) {
  const { bid_ntce_no } = await params;
  const lifecycle = await fetchLifecycle(bid_ntce_no);
  if (!lifecycle) notFound();
  const { notice, insight } = lifecycle;
  const lc = toLifecycleData(lifecycle);

  return (
    <div className="pb-20">
      <JsonLd
        data={noticeJsonLd({
          bidNtceNo: notice.bid_ntce_no,
          bidNtceNm: notice.bid_ntce_nm,
          // formatKRW·formatDateKR 은 값이 없으면 "—" 를 준다 — "추정 — · 마감 —" 이 안 들어가게 유효한 절만 잇는다.
          description: [
            notice.dmnd_instt_nm ?? notice.ntce_instt_nm ?? null,
            notice.bsns_div_nm,
            formatKRW(notice.presmpt_prce) !== "—" ? `추정 ${formatKRW(notice.presmpt_prce)}` : null,
            notice.bid_clse_date && formatDateKR(notice.bid_clse_date) !== "—" ? `마감 ${formatDateKR(notice.bid_clse_date)}` : null,
          ]
            .filter(Boolean)
            .join(" · "),
          instituionName: notice.dmnd_instt_nm ?? notice.ntce_instt_nm,
          regionName: notice.prtcpt_psbl_rgn_nm,
          validFrom: notice.bid_ntce_date,
          validThrough: notice.bid_clse_date,
        })}
      />

      <header className="mt-8 border-b border-ink pb-3.5 max-sm:mt-5">
        <h1 className="text-[24px] font-[650] leading-[1.35] tracking-[-0.02em] text-ink max-sm:text-[19px]">{notice.bid_ntce_nm}</h1>
        <p className="mt-1.5 text-[13.5px] text-ink-g">
          {notice.dmnd_instt_nm || notice.ntce_instt_nm || "—"}
          {notice.bsns_div_nm && <> · {notice.bsns_div_nm}</>}
          <span className="num"> · 공고번호 {notice.bid_ntce_no}</span>
        </p>
      </header>

      <div className="mt-5 grid grid-cols-[260px_minmax(0,1fr)] items-start gap-x-10 max-sm:grid-cols-1 max-sm:gap-y-6">
        <NoticeRailClient n={notice} />
        <div className="min-w-0 rounded-[6px] border border-hair bg-panel px-6 py-5 max-sm:px-4">
          <WorkSection n={notice} insight={insight} />
          <RequirementsSection insight={insight} />
          <StagesSection lc={lc} />
          <InstitutionSection n={notice} />
        </div>
      </div>
    </div>
  );
}
