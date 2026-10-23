// frontend/src/app/(renewal)/dev/foundation/page.tsx
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel, PanelHead } from "@/components/Panel";
import { StarCompany } from "@/components/StarCompany";
import { getSessionUser } from "@/lib/auth";
import { getReviewedKeys, getSavedCompanyKeys } from "@/lib/saved";
import { Sheet } from "./sheet";
import { maskBizrno } from "@/lib/utils";

export const metadata: Metadata = { title: "foundation", robots: { index: false, follow: false } };

/** 부품 전시 — 09 컷오버에서 삭제. 값은 data/sample.json(한종산업개발, 2026-10-16 실제 추천) 첫 세 건. */
export default async function FoundationPage() {
  const user = await getSessionUser();
  const [stars, reviews] = user ? await Promise.all([getSavedCompanyKeys(), getReviewedKeys()]) : [new Set<string>(), new Set<string>()];
  const loggedIn = !!user;
  return (
    <>
      <PageHead title="한종산업개발 주식회사" small={maskBizrno("1248177731")}
        aside={<StarCompany bizrnoNorm="1248177731" saved={stars.has("1248177731")} loggedIn={loggedIn} className="ml-3 h-[30px] text-[13px]" />}
        meta={["경상남도 창원시", "등록업종 15", "공급물품 없음", "기준일 2026-10-16"]} />
      <Panel className="mt-[22px]">
        <PanelHead title="검토할 공고 12건" small="적합 순" />
        <Sheet loggedIn={loggedIn} reviewed={[...reviews]} />
      </Panel>
      <Panel className="mt-7">
        <PanelHead title="수주 이력" small="계약 7건 · 2026.06.26 ~ 2026.09.30" summary={[<>누적 <b>268.2억</b></>, <>주요 발주기관 경상남도 창원시</>]} />
        <p className="pt-4 text-[14px] text-ink-body">표 본문은 06 회사 계획에서.</p>
      </Panel>
      <div className="mt-7 flex flex-wrap gap-2">
        <Btn variant="dark">나라장터 원문</Btn><Btn variant="review">검토</Btn><Btn variant="review" on>검토함</Btn><Btn variant="line">수정 요청</Btn>
        <Btn variant="text"><u>취소 · Esc</u></Btn><Btn variant="dark" disabled>가입</Btn>
      </div>
    </>
  );
}
