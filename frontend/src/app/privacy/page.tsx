import type { Metadata } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
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
      <Header />
      <main className="world-gc flex-1">
        <article className="mx-auto max-w-[820px] px-5 sm:px-8 py-12 sm:py-16 text-[15px] leading-[1.8] text-foreground/85 break-keep">
          <h1 className="font-gc-serif font-black text-[28px] sm:text-[34px] tracking-[-0.02em] text-gc-ink">
            개인정보처리방침
          </h1>
          <p className="mt-2 text-[13.5px] text-muted-foreground">시행일 {PRIVACY_VERSION}</p>

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
              ]}
            />
            <p className="mt-3">
              IP 주소는 원래 값을 저장하지 않고, 되돌릴 수 없는 값으로 변환해 저장합니다. 이름·전화번호·
              주민등록번호는 받지 않습니다.
            </p>
          </Section>

          <Section title="2. 보관 기간과 파기">
            <ul className="list-disc pl-5 space-y-1">
              <li>이메일 주소: 구독을 해지하거나 삭제를 요청할 때까지</li>
              <li>검색·이용 기록: 수집일로부터 1년이 지나면 자동으로 삭제합니다</li>
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
                ["Supabase Inc.", "데이터 저장", "인도 (AWS 뭄바이)", "1번의 모든 항목"],
                ["Vercel Inc.", "웹페이지 제공, 메일 신청 접수", "싱가포르", "이메일 주소, 접속 정보"],
                ["Railway Corporation", "추천 계산 서버", "싱가포르", "검색어, 접속 정보"],
                ["OpenAI, L.L.C.", "검색어 의미 분석", "미국", "검색어"],
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
              조달핏의 기업 페이지는 나라장터 등 공공데이터에 공개된 정보(등록업종, 공급물품, 계약·낙찰
              내역)를 기업별로 정리한 것입니다. 해당 기업이 원하지 않으면 비공개로 처리합니다.
            </p>
            <ul className="mt-3 list-disc pl-5 space-y-1">
              <li>
                요청 방법: 상호, 사업자등록번호, 요청 내용을 적어{" "}
                <a href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("[조달핏] 기업 정보 비공개 요청")}`} className="underline underline-offset-2">
                  {CONTACT_EMAIL}
                </a>
                로 보내주세요.
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
      </main>
      <Footer className="mt-0" />
    </>
  );
}

function Section({ id, title, children }: { id?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-10 scroll-mt-24">
      <h2 className="font-gc-serif font-black text-[19px] sm:text-[21px] tracking-[-0.01em] text-gc-ink">
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
        <thead className="bg-muted/60 text-[12.5px] font-semibold text-muted-foreground">
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
