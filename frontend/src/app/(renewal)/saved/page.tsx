// frontend/src/app/(renewal)/saved/page.tsx
// 검토함 — 로그인 사용자 전용. 비로그인은 리다이렉트가 아니라 안내 판(마스터 §3.2). 세션 쿠키를 읽으므로 항상 동적.
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { getSessionUser } from "@/lib/auth";
import { getReviewedNotices, getSavedCompanies } from "@/lib/saved";
import { CompanyRows } from "./CompanyRows";
import { NoticeRows } from "./NoticeRows";
import { SavedTabs } from "./SavedTabs";

export const metadata: Metadata = { title: "검토함 | 조달핏", robots: { index: false, follow: false } };

export default async function SavedPage() {
  const user = await getSessionUser();
  if (!user) {
    return (
      <>
        <PageHead title="검토함" />
        <Panel className="mt-[22px]">
          <div data-saved-gate className="flex flex-wrap items-center gap-3.5 pb-2.5 pt-[26px] text-[14.5px]">
            <div>
              <b className="font-semibold text-ink">검토함은 로그인 후 사용</b>
              <span className="mt-1 block text-[13.5px] text-ink-dim">검토 표시한 공고와 저장한 회사를 보관</span>
            </div>
            <span className="grow" />
            <span className="flex gap-2">
              <Btn href="/login?next=%2Fsaved">로그인</Btn>
              <Btn variant="dark" href="/signup?next=%2Fsaved">회원가입</Btn>
            </span>
          </div>
        </Panel>
      </>
    );
  }
  const today = new Date();
  const [{ live, past }, companies] = await Promise.all([getReviewedNotices(today), getSavedCompanies(today)]);
  return (
    <SavedTabs
      counts={{ n: live.length, c: companies.length }}
      notices={<NoticeRows live={live} past={past} />}
      companies={<CompanyRows rows={companies} />}
    />
  );
}
