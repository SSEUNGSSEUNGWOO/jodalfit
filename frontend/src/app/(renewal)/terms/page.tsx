import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { TERMS_VERSION } from "@/lib/terms";
import { CONTACT_EMAIL } from "@/lib/privacy";

export const metadata: Metadata = { title: "이용약관 | 조달핏", alternates: { canonical: "/terms" } };

const H = "mt-8 mb-2 text-[16px] font-semibold text-ink";
const P = "m-0 text-[14.5px] leading-[1.75] text-ink-body";
const L = "m-0 list-decimal pl-5 text-[14.5px] leading-[1.75] text-ink-body [&>li]:mt-1";

export default function TermsPage() {
  return (
    <>
      <PageHead title="이용약관" meta={[`시행 ${TERMS_VERSION}`]} />
      <Panel className="mt-[22px] pt-2">
        <h2 className={H}>제1조 (목적)</h2>
        <p className={P}>이 약관은 조달핏(이하 &ldquo;서비스&rdquo;)이 제공하는 공공입찰 공고 추천 및 관련 정보 제공 서비스의 이용 조건과 절차, 이용자와 서비스 운영자의 권리·의무를 정합니다.</p>
        <h2 className={H}>제2조 (정의)</h2>
        <ol className={L}>
          <li>&ldquo;이용자&rdquo;란 이 약관에 동의하고 서비스를 이용하는 자를 말합니다.</li>
          <li>&ldquo;계정&rdquo;이란 이메일과 비밀번호로 식별되는 이용자 단위를 말합니다.</li>
          <li>&ldquo;콘텐츠&rdquo;란 서비스가 나라장터(국가종합전자조달) 등 공공데이터를 바탕으로 가공·표시하는 공고, 회사 정보, 추천 결과, 근거 설명을 말합니다.</li>
        </ol>
        <h2 className={H}>제3조 (약관의 효력과 변경)</h2>
        <ol className={L}>
          <li>이 약관은 서비스 화면에 게시함으로써 효력이 발생합니다.</li>
          <li>운영자는 관련 법령을 위반하지 않는 범위에서 약관을 변경할 수 있으며, 변경 시 시행일 7일 전부터 서비스 화면에 공지합니다. 이용자에게 불리한 변경은 30일 전에 공지합니다.</li>
          <li>이용자가 변경 약관 시행 후에도 서비스를 계속 이용하면 변경에 동의한 것으로 봅니다.</li>
        </ol>
        <h2 className={H}>제4조 (서비스의 내용)</h2>
        <ol className={L}>
          <li>서비스는 이용자가 입력한 회사명·사업자등록번호 또는 키워드를 기준으로 검토할 만한 공고를 추천하고, 추천 근거와 참가 자격 판정, 공고·회사 관련 정보를 표시합니다.</li>
          <li>추천은 검토 순서를 제안하는 것이며 낙찰 가능성을 예측하거나 보장하지 않습니다. 참가 자격 판정은 공고 필드(허용업종·지역·등록 마감)에 한하며, 입찰 서류상의 요건은 이용자가 원문에서 확인해야 합니다.</li>
          <li>콘텐츠의 원천은 공공데이터이며, 서비스는 매일 갱신하되 원천의 오류·지연에 대해 책임지지 않습니다.</li>
          <li>운영자는 서비스의 전부 또는 일부를 변경·중단할 수 있으며, 유료 기능을 도입할 경우 사전에 공지합니다.</li>
        </ol>
        <h2 className={H}>제5조 (계정)</h2>
        <ol className={L}>
          <li>계정은 이메일 확인을 거쳐 생성됩니다. 이용자는 정확한 이메일을 제공하고 비밀번호를 안전하게 관리할 책임이 있습니다.</li>
          <li>계정은 양도·대여할 수 없습니다.</li>
          <li>이용자는 언제든 탈퇴할 수 있으며, 탈퇴 시 계정과 저장한 회사·검토한 공고 기록은 삭제됩니다.</li>
        </ol>
        <h2 className={H}>제6조 (이용자의 의무)</h2>
        <ol className={L}>
          <li>자동화 수단으로 콘텐츠를 대량 수집하거나 서비스 운영을 방해하는 행위를 하지 않습니다.</li>
          <li>타인의 정보를 도용하거나 서비스를 법령에 위반하는 목적으로 이용하지 않습니다.</li>
          <li>운영자는 위 의무를 위반한 계정의 이용을 제한할 수 있습니다.</li>
        </ol>
        <h2 className={H}>제7조 (지식재산권)</h2>
        <p className={P}>서비스의 화면 구성, 추천 방식, 가공된 콘텐츠에 대한 권리는 운영자에게 있습니다. 공공데이터 원문의 권리는 해당 기관에 있으며, 이용자는 콘텐츠를 입찰 검토 목적으로 이용할 수 있습니다.</p>
        <h2 className={H}>제8조 (책임의 한계)</h2>
        <ol className={L}>
          <li>서비스는 무료로 제공되는 범위에서 &ldquo;있는 그대로&rdquo; 제공되며, 운영자는 콘텐츠의 정확성·완전성·특정 목적 적합성을 보증하지 않습니다.</li>
          <li>이용자가 서비스의 추천·판정을 근거로 내린 입찰 결정의 결과에 대해 운영자는 책임지지 않습니다.</li>
          <li>천재지변, 원천 데이터 제공 중단, 통신 장애 등 운영자가 통제할 수 없는 사유로 인한 손해에 대해 책임지지 않습니다.</li>
        </ol>
        <h2 className={H}>제9조 (개인정보)</h2>
        <p className={P}>개인정보의 수집·이용·보관은 <a href="/privacy" className="u-link text-ink">개인정보처리방침</a>에 따릅니다.</p>
        <h2 className={H}>제10조 (준거법과 분쟁)</h2>
        <p className={P}>이 약관은 대한민국 법령에 따르며, 서비스 이용과 관련한 분쟁은 운영자 소재지를 관할하는 법원을 제1심 관할 법원으로 합니다.</p>
        <h2 className={H}>부칙</h2>
        <p className={P}>이 약관은 {TERMS_VERSION}부터 시행합니다. 문의 {CONTACT_EMAIL}</p>
      </Panel>
    </>
  );
}
