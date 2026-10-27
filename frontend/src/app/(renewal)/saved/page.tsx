// frontend/src/app/(renewal)/saved/page.tsx
// 검토함 — 로그인 사용자 전용. 비로그인은 리다이렉트가 아니라 안내 판(마스터 §3.2). 세션 쿠키를 읽으므로 항상 동적.
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { getSessionUser } from "@/lib/auth";
import { weeklyMailToken } from "@/lib/mail-link";
import { getReviewedNotices, getSavedCompanies } from "@/lib/saved";
import { getServerSupabase } from "@/lib/supabase-server";
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
  const [{ live, past }, companies, consent] = await Promise.all([
    getReviewedNotices(today), getSavedCompanies(today),
    getServerSupabase().from("user_consents").select("marketing_opt_in").eq("user_id", user.id).maybeSingle(),
  ]);
  const weeklyOn = !!(consent.data as { marketing_opt_in: boolean } | null)?.marketing_opt_in;
  return (
    <>
      <SavedTabs
        counts={{ n: live.length, c: companies.length }}
        notices={<NoticeRows live={live} past={past} />}
        companies={<CompanyRows rows={companies} />}
      />
      <WeeklyMailLine userId={user.id} on={weeklyOn} />
    </>
  );
}

/** 주간 메일(jobs/send_weekly_mail, 2026-10-27) — 저장한 회사에 새 공고가 있는 주에 월요일 아침 한 통. 켜고 끄는 열은 0052 user_consents.marketing_opt_in.
 *  바꾸기는 메일 하단 링크와 같은 폼(/api/mail/weekly POST, HMAC 토큰) — 경로를 둘로 두지 않는다. */
function WeeklyMailLine({ userId, on }: { userId: string; on: boolean }) {
  const t = weeklyMailToken(userId);
  return (
    <p data-weekly-mail data-on={on ? "1" : "0"} className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-hair pt-4 text-[13.5px] text-ink-g">
      <span>저장한 회사에 새 공고가 있으면 매주 월요일 아침 메일로 보냅니다.</span>
      <b className="font-semibold text-ink">{on ? "받는 중" : "받지 않음"}</b>
      {t && (
        <form method="post" action="/api/mail/weekly" className="inline">
          <input type="hidden" name="u" value={userId} /><input type="hidden" name="t" value={t} /><input type="hidden" name="on" value={on ? "0" : "1"} /><input type="hidden" name="back" value="saved" />
          <button type="submit" className="cursor-pointer border-b border-field text-ink hover:border-orange">{on ? "그만 받기" : "받기"}</button>
        </form>
      )}
    </p>
  );
}
