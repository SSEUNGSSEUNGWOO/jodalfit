// frontend/src/app/dev/foundation/sheet.tsx
"use client";

import { Btn } from "@/components/Btn";
import { Gate } from "@/components/Gate";
import { SheetExpand, SheetFade, SheetHead, SheetRow } from "@/components/Sheet";
import { dLeft, won } from "@/lib/format";

const TODAY = new Date(2026, 9, 16);
// data/sample.json results[0..2] + fade 용 results[5]
const ROWS = [
  { no: 1, title: "송탄정수장 공업용수공급 시설공사(1공구)", org: "경기도 평택시 상하수도사업소", why: "재출현 기관", clse: "2026-10-29", price: 5025454546, reviewed: true,
    quals: [{ state: "none", text: "면허 — 제한 없음" }, { state: "none", text: "지역 — 제한 없음" }, { state: "todo", text: "규모 — 중소기업 확인서 요구 여부는 문서 조건에서, 회사 규모 미입력" }] as const,
    whys: ["경기도 평택시 상하수도사업소 — 과거 거래 이력 있음", "추정가가 회사 평균 수주가의 1.08배 — 유사한 규모", "공고 내용과 회사 업종 설명 유사도 73%"] },
  { no: 2, title: "중랑물재생센터 제1처리장 관리대행", org: "서울특별시 물재생센터 중랑물재생센터", why: "업종·물품 일치", clse: "2026-11-25", price: 6106074545, reviewed: false, quals: [], whys: [] },
  { no: 3, title: "송탄정수장 공업용수공급 시설공사(2공구)", org: "경기도 평택시 상하수도사업소", why: "재출현 기관", clse: "2026-10-29", price: 7690000000, reviewed: false, quals: [], whys: [] },
];

export function Sheet() {
  return (
    <>
      <SheetHead />
      {ROWS.map((r) => (
        <SheetRow key={r.no} no={r.no} title={r.title} org={r.org} why={r.why} dLeft={dLeft(r.clse, TODAY)} price={won(r.price)} reviewed={r.reviewed} defaultOpen={r.no === 1}>
          {r.quals.length > 0 && (
            <SheetExpand quals={[...r.quals]} whys={r.whys} actions={<><Btn variant="dark" href="https://www.g2b.go.kr">나라장터 원문</Btn><Btn variant="review">검토</Btn></>} />
          )}
        </SheetRow>
      ))}
      <Gate rest={7} next="/dev/foundation" />
      <SheetFade>
        <SheetRow no={6} title="중랑물재생센터 일부시설물 관리대행" org="서울특별시 물재생센터 중랑물재생센터" why="업종·물품 일치" dLeft={dLeft("2026-11-24", TODAY)} price={won(19974684545)} />
        <SheetRow no={7} title="양산하수처리장 악취저감사업 실시설계용역" org="경상남도 양산시 상하수도사업소" why="지역 매칭" dLeft={dLeft("2026-10-20", TODAY)} price={won(58081818)} />
      </SheetFade>
    </>
  );
}
