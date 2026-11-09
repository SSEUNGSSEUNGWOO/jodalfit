// frontend/src/app/(renewal)/privacy/page.tsx
// 개인정보처리방침 — 09 전환에서 리뉴얼 껍데기로 옮겼다. nav·footer 는 레이아웃이 준다.
import type { Metadata } from "next";
import { CONTACT_EMAIL, PRIVACY_VERSION } from "@/lib/privacy";

export const metadata: Metadata = {
  title: "개인정보처리방침 | 조달핏",
  description:
    "조달핏이 수집하는 개인정보 항목과 이용 목적, 보관 기간, 처리 위탁과 국외 이전, 정보주체의 권리, 공개된 기업 정보의 비공개 요청 방법을 안내합니다.",
  alternates: { canonical: "/privacy" },
};

// 이 페이지의 모든 문장은 실제 코드 동작과 맞아야 한다. 수집 항목이나 위탁처(예: 메일 발송
// 서비스, DB 리전 이전)가 바뀌면 이 페이지와 lib/privacy.ts 의 PRIVACY_VERSION 을 같이 고친다.

export default function PrivacyPage() {
  return (
    <>
      <div>
        <article className="mx-auto max-w-[820px] px-5 sm:px-8 py-12 sm:py-16 text-[15px] leading-[1.8] text-ink-g break-keep">
          <h1 className="font-[650] text-[28px] sm:text-[34px] tracking-[-0.02em] text-ink">
            개인정보처리방침
          </h1>
          <p className="mt-2 text-[13.5px] text-ink-mute">시행일 {PRIVACY_VERSION}</p>

          <p className="mt-6">
            조달핏(이하 &ldquo;서비스&rdquo;)은 회원가입 없이 쓸 수 있도록 만들어, 개인정보를 최소한으로만
            처리합니다. 아래는 서비스가 실제로 수집하는 항목과 그 처리 방식입니다.
          </p>

          <Section title="1. 수집 항목과 이용 목적">
            <Table
              head={["항목", "언제", "이용 목적"]}
              rows={[
                ["이메일 주소, (선택) 관심 회사", "주간 추천 메일을 신청할 때", "주간 추천 메일과 서비스 소식 발송"],
                [
                  "검색어, IP 주소(복원할 수 없게 변환한 값), 브라우저 정보, 유입 경로, 이용 시각",
                  "공고를 검색할 때 자동으로",
                  "서비스 운영과 오류 분석, 부정 이용 방지, 이용 통계",
                ],
                ["브라우저 탭 단위 임시 식별값, 공고 클릭·저장 기록", "공고를 클릭하거나 저장할 때", "추천 품질 개선"],
                [
                  "이메일 주소, 비밀번호(해시로만 저장), 동의 기록(이용약관·개인정보처리방침 버전, 알림 메일 수신 여부, 동의 시각), 저장한 회사·검토한 공고",
                  "가입하고 로그인할 때",
                  "로그인과 계정 식별, 검토함·저장한 회사 보관, 동의 이력 보존",
                ],
                [
                  "이메일 주소, 해당 서비스의 회원 식별값(구글·네이버가 발급한 고유 ID)",
                  "구글 또는 네이버 계정으로 로그인할 때 그 서비스에서 받음",
                  "비밀번호 없는 로그인과 계정 식별. 이름·프로필 사진 등 그 밖의 정보는 받지 않음",
                ],
                [
                  "의견·문의 내용, (선택) 답장받을 이메일 주소, 보내기 전에 보던 페이지 주소, IP 주소(복원할 수 없게 변환한 값), 브라우저 정보",
                  "의견 보내기 폼으로 보낼 때",
                  "문의 답변, 오류 확인과 서비스 개선, 부정 이용 방지",
                ],
              ]}
            />
            <p className="mt-3">
              IP 주소는 원래 값을 저장하지 않고, 되돌릴 수 없는 값으로 변환해 저장합니다. 이름·전화번호·
              주민등록번호는 받지 않습니다.
            </p>
            <p className="mt-3">
              가입 때 알림 메일 수신에 동의한 회원에게는 검토함에 저장한 회사에 새 공고가 있는 주에 한해 매주 월요일
              아침 메일 한 통을 보냅니다(발송 기록은 보관 기간 1년). 메일 하단 링크나 검토함에서 언제든 받지 않도록 바꿀 수 있습니다.
            </p>
          </Section>

          <Section title="2. 보관 기간과 파기">
            <ul className="list-disc pl-5 space-y-1">
              <li>이메일 주소: 구독을 해지하거나 삭제를 요청할 때까지</li>
              <li>검색·이용 기록: 수집일로부터 1년이 지나면 자동으로 삭제합니다</li>
              <li>계정 정보: 탈퇴 시 즉시 삭제합니다(법령상 보존 의무가 있는 기록 제외). 로그인 기록은 1년</li>
              <li>의견·문의: 답변과 처리가 끝난 뒤 1년이 지나면 삭제합니다. 삭제를 요청하면 즉시 삭제합니다</li>
            </ul>
          </Section>

          <Section title="3. 제3자 제공">
            <p>개인정보를 제3자에게 제공하지 않습니다.</p>
          </Section>

          <Section title="4. 처리 위탁과 국외 이전">
            <p>서비스 운영을 위해 아래 업체의 시스템을 이용하며, 이 과정에서 정보가 국외에서 처리됩니다.</p>
            <Table
              head={["업체", "맡기는 일", "처리 위치", "이전 항목"]}
              rows={[
                ["Supabase Inc.", "데이터 저장", "싱가포르 (AWS)", "1번의 모든 항목"],
                ["Vercel Inc.", "웹페이지 제공, 메일 신청 접수", "싱가포르", "이메일 주소, 접속 정보"],
                ["Railway Corporation", "추천 계산 서버", "싱가포르", "검색어, 접속 정보"],
                ["Google LLC", "검색어 의미 분석", "미국", "검색어"],
                ["Anthropic, PBC", "추천 설명 문장 생성", "미국", "검색어"],
                ["OpenAI, L.L.C.", "추천 설명 문장 생성(위 업체 장애 시 예비)", "미국", "검색어"],
                ["PostHog, Inc.", "이용 통계 분석", "미국", "접속 정보"],
                ["Functional Software, Inc. (Sentry)", "오류 기록", "미국", "접속 정보"],
                ["Resend", "가입 확인·비밀번호 재설정 메일 발송", "미국", "이메일 주소"],
              ]}
            />
            <p className="mt-3">
              정보는 서비스를 이용하는 시점에 암호화된 네트워크로 전송되며, 보관 기간은 2번과 같습니다.
              국외 이전을 원하지 않으시면 이메일 신청이나 검색을 하지 않으시면 되고, 이미 수집된 정보는
              7번 연락처로 삭제를 요청하실 수 있습니다.
            </p>
          </Section>

          <Section title="5. 쿠키와 브라우저 저장소">
            <p>
              쿠키는 사용하지 않습니다. 대신 브라우저 저장소에 두 가지를 둡니다. 탭을 닫으면 사라지는 임시
              식별값(sessionStorage), 그리고 직접 저장한 &ldquo;검토 목록&rdquo;(localStorage)입니다.
              검토 목록은 서버로 보내지 않고 그 브라우저에만 남습니다. 브라우저 설정에서 언제든 지울 수 있습니다.
            </p>
          </Section>

          <Section title="6. 정보주체의 권리">
            <p>
              자신의 개인정보에 대해 열람·정정·삭제·처리정지를 요청할 수 있습니다. 7번 연락처로 메일을
              보내주시면 확인 후 지체 없이 처리하고 결과를 회신합니다.
            </p>
          </Section>

          <Section title="7. 개인정보 보호책임자">
            <p>
              조달핏 운영자 ·{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="underline underline-offset-2">
                {CONTACT_EMAIL}
              </a>
            </p>
          </Section>

          <Section id="company-optout" title="8. 공개된 기업 정보의 비공개 요청">
            <p>
              조달핏의 기업 페이지는 나라장터 등 공공기관이 공공데이터법에 따라 공개한 기업 단위 정보(등록업종, 공급물품,
              계약·낙찰 내역)를 기업별로 정리한 것입니다. 조달핏은 공공데이터의 제공 조건과 관계 법령을 지켜 이 정보를
              이용하며, 법인에 관한 정보는 원칙적으로 개인정보보호법의 보호 대상인 개인정보가 아닙니다. 따라서 단순히 게시를
              원하지 않는다는 이유만으로는 게시를 중단할 의무가 생기지 않으며, 그러한 요구에는 응하지 않습니다.
            </p>
            <p className="mt-2">
              개인정보는 공개하지 않습니다. 대표자 성명 등 개인을 식별할 수 있는 항목은 어떤 화면이나 응답에도 내보내지
              않으며, 사업자등록번호는 일부를 가려 표시합니다. 개인사업자 등 개인을 식별할 수 있는 정보의 당사자가 요청하거나
              게시된 정보가 사실과 다른 경우에는 본인·권한을 확인한 뒤 관계 법령에 따라 처리하고, 처리 결과와 사유를 알립니다.
            </p>
            <p className="mt-2">
              그 밖의 기업이 게시를 원하지 않는 경우, 아래 요건을 모두 갖춘 요청에 한해 조달핏이 검토한 뒤 재량으로 비공개 처리할
              수 있습니다. 이 비공개 처리는 법령상 의무가 아닌 조치입니다. 요건을 갖추지 않은 요청에는 보완을 요구하며 보완되지
              않으면 처리하지 않고, 같은 내용의 반복 요청과 위협적이거나 모욕적인 표현이 포함된 요청에는 회신하지 않습니다.
            </p>
            <ul className="mt-3 list-disc pl-5 space-y-1">
              <li>
                요청 방법: 상호, 사업자등록번호, 요청 사유, 요청자의 소속과 연락처를 적어{" "}
                <a href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("[조달핏] 기업 정보 비공개 요청")}`} className="underline underline-offset-2">
                  {CONTACT_EMAIL}
                </a>
                로 보냅니다. 요건을 갖춘 요청에는 영업일 기준 7일 안에 회신합니다.
              </li>
              <li>
                본인 확인: 요청자가 해당 기업의 대표자이거나 기업으로부터 권한을 위임받은 담당자임이 확인되어야 합니다. 해당 기업의
                도메인으로 된 메일 주소에서 온 요청은 그것으로 확인합니다. 다른 메일 주소로 온 요청은 사업자등록증 사본, 재직이나
                위임을 확인할 수 있는 자료를 요구하며, 나라장터에 등록된 기업 정보와 대조합니다. 확인 자료는 확인 목적에만 쓰고
                확인이 끝나면 지체 없이 파기합니다.{" "}
                <strong className="font-[650] text-ink">요청자가 그 기업임을 확인할 수 없으면 보완을 요구하고, 확인되지 않은 요청은 처리하지 않습니다.</strong>
              </li>
              <li>
                처리 내용: 기업 상세페이지를 내리고, 기업 목록·검색·사이트맵에서 제외하며, 입찰공고
                페이지의 계약·낙찰 정보에서도 상호를 가립니다. 이후 데이터가 갱신되어도 다시 공개되지 않습니다.
              </li>
              <li>
                이미 검색엔진에 올라간 결과는 검색엔진 측에 삭제를 요청합니다. 실제로 사라지기까지는 각
                검색엔진의 처리 일정에 따라 시간이 걸릴 수 있습니다.
              </li>
            </ul>
          </Section>

          <Section title="9. 권익 침해 구제">
            <p>개인정보 침해에 대한 신고나 상담은 아래 기관에 하실 수 있습니다.</p>
            <ul className="mt-3 list-disc pl-5 space-y-1">
              <li>개인정보침해신고센터 (국번없이 118, privacy.kisa.or.kr)</li>
              <li>개인정보분쟁조정위원회 (1833-6972, www.kopico.go.kr)</li>
              <li>대검찰청 (국번없이 1301)</li>
              <li>경찰청 (국번없이 182, ecrm.police.go.kr)</li>
            </ul>
          </Section>

          <Section title="10. 방침의 변경">
            <p>이 방침을 바꾸면 이 페이지에 시행일과 함께 알립니다.</p>
          </Section>
        </article>
      </div>
    </>
  );
}

function Section({ id, title, children }: { id?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-10 scroll-mt-24">
      <h2 className="font-[650] text-[19px] sm:text-[21px] tracking-[-0.01em] text-ink">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-background">
      <table className="w-full min-w-[520px] text-[13.5px] leading-[1.6]">
        <thead className="bg-muted/60 text-[12.5px] font-semibold text-ink-mute">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-4 py-2.5 text-left">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r[0]} className="border-t border-border align-top">
              {r.map((c, i) => (
                <td key={i} className="px-4 py-2.5">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
