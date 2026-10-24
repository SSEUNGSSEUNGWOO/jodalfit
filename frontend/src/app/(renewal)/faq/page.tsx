// frontend/src/app/(renewal)/faq/page.tsx
// 자주 묻는 질문 — 입찰 담당자가 검색엔진·AI 에게 물을 법한 질문에 바로 답하는 문서(GEO, 2026-10-24).
// 답은 운영 코드·문서와 같은 사실만 쓴다. 점수표 숫자는 개선 기록(/changelog '어떻게 고르는가')이 score.py 에서
// 검사받으므로 여기서는 되풀이하지 않는다 — 두 곳에 적으면 한쪽이 낡는다.
// FAQPage 구조화 데이터는 화면과 같은 문장(구글 지침: 보이는 내용만).
import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { faqJsonLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "자주 묻는 질문 | 조달핏",
  description: "조달핏이 나라장터 공고를 고르는 기준, 참가 자격 판정 방식, 데이터 갱신 주기, 이용 방법에 대한 답.",
  alternates: { canonical: "/faq" },
};

const FAQ = [
  {
    q: "조달핏은 무엇입니까?",
    a: "나라장터(국가종합전자조달) 입찰공고 중 특정 회사가 검토할 만한 공고를 추리는 서비스입니다. 회사명이나 사업자등록번호를 입력하면 그 회사의 등록업종·공급물품·수주 이력을 함께 분석해, 지금 입찰 가능한 공고 가운데 참가 자격이 있고 회사와 비슷한 공고를 적합 순으로 보여 줍니다.",
  },
  {
    q: "낙찰 가능성을 알려 줍니까?",
    a: "아닙니다. 추천 순서는 검토할 공고를 놓치지 않기 위한 순서이며 낙찰 확률이 아닙니다. 낙찰 여부는 가격·평가·경쟁 상황에 달려 있어 공개 데이터만으로 예측하지 않습니다.",
  },
  {
    q: "회사로 찾기와 키워드로 찾기는 무엇이 다릅니까?",
    a: "회사로 찾기는 그 회사의 등록업종·공급물품·수주 이력을 기준으로 공고를 고르고 참가 자격까지 판정합니다. 키워드로 찾기는 입력한 업종·품목과 의미가 가까운 공고를 찾으며, 회사 정보가 없으므로 참가 자격은 판정하지 않습니다. 회사명으로 찾지 못하면 키워드 검색으로 넘어갑니다.",
  },
  {
    q: "추천은 어떤 순서로 고릅니까?",
    a: "지금 입찰 가능한 공고 전체에서 회사와 비슷한 공고를 후보로 추리고, 참가 자격이 없는 공고를 뺀 뒤, 유사도에 과거 거래 기관·지역·업종 표현 일치·예산 규모·마감 임박 같은 신호를 더한 점수 순으로 정렬합니다. 신호별 점수와 그 근거는 개선 기록 페이지의 '어떻게 고르는가'에 운영 코드 값 그대로 공개합니다.",
  },
  {
    q: "참가 자격은 어떻게 판정합니까?",
    a: "공고에 적힌 제한 세 가지를 대조합니다. 면허(허용업종) 제한은 공고가 요구하는 면허 그룹 중 하나에 회사 등록업종이 포함되면 통과입니다. 지역 제한은 공고가 제한한 단위(시·도 또는 시·군·구)까지 회사 소재지를 비교합니다. 입찰참가자격 등록 마감이 지난 공고는 지금 등록하려는 회사가 낼 수 없어 뺍니다. 첨부 문서에 적힌 실적·증명 요건은 판정하지 않으므로 공고 원문으로 확인해야 합니다.",
  },
  {
    q: "데이터는 어디서 오고 얼마나 자주 갱신됩니까?",
    a: "나라장터 공공데이터 API(조달청)에서 수집합니다. 입찰공고는 매시 수집하고, 계약·낙찰·업체 정보와 회사별 분석은 매일 오전 5시(한국 시간)에 갱신합니다.",
  },
  {
    q: "사전규격과 발주계획은 무엇입니까?",
    a: "사전규격은 기관이 입찰공고 전에 규격을 미리 공개하고 업체 의견을 받는 단계이고, 발주계획은 기관이 앞으로 발주할 사업을 미리 알린 계획입니다. 둘 다 공고가 나오기 전에 준비할 시간을 줍니다. 회사로 찾으면 결과 아래 '공고 전 단계'에 함께 보여 줍니다.",
  },
  {
    q: "무료입니까? 회원가입이 필요합니까?",
    a: "현재 무료입니다. 추천 결과 상위 5건은 로그인 없이 볼 수 있고, 나머지와 검토함·회사 저장은 이메일과 비밀번호로 가입한 뒤 쓸 수 있습니다.",
  },
  {
    q: "우리 회사 정보가 공개되는 것을 막을 수 있습니까?",
    a: "가능합니다. 개인정보처리방침의 '기업 정보 비공개 요청'으로 요청하면 회사 페이지와 다른 페이지에서의 노출을 막습니다. 사업자등록번호는 처음부터 가려서(예: 124-XX-X731) 표시합니다.",
  },
] as const;

const LINKS: Record<number, { href: string; label: string }> = {
  3: { href: "/changelog", label: "개선 기록 — 어떻게 고르는가" },
  8: { href: "/privacy#company-optout", label: "기업 정보 비공개 요청" },
};

export default function FaqPage() {
  return (
    <>
      <JsonLd data={faqJsonLd(FAQ)} />
      <PageHead title="자주 묻는 질문" meta={["나라장터 공공데이터 기반 · 매일 갱신"]} />
      <Panel className="mt-[22px] pt-2">
        {FAQ.map((it, i) => (
          <section key={it.q} className="border-b border-rule py-5 last:border-b-0">
            <h2 className="m-0 text-[16px] font-semibold text-ink">{it.q}</h2>
            <p className="mt-2 mb-0 max-w-[760px] text-[14.5px] leading-[1.75] text-ink-body">{it.a}</p>
            {LINKS[i] && (
              <a href={LINKS[i].href} className="mt-2 inline-block border-b border-field text-[13px] text-ink-g hover:border-orange">
                {LINKS[i].label} →
              </a>
            )}
          </section>
        ))}
      </Panel>
    </>
  );
}
