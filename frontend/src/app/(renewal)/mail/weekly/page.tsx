// frontend/src/app/(renewal)/mail/weekly/page.tsx
// 주간 메일 "그만 받기" 착지 — 메일 링크(u, t)로 오면 확인 버튼 하나, 누르면 /api/mail/weekly (POST) 가 바꾸고 done= 으로 돌아온다.
import type { Metadata } from "next";
import { Btn } from "@/components/Btn";
import { PageHead } from "@/components/PageHead";
import { Panel } from "@/components/Panel";
import { verifyWeeklyMailToken } from "@/lib/mail-link";

export const metadata: Metadata = { title: "주간 메일 수신 | 조달핏", robots: { index: false, follow: false } };

export default async function WeeklyMailPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const p = await searchParams;
  const one = (k: string) => { const v = p[k]; return (Array.isArray(v) ? v[0] : v) ?? ""; };
  const done = one("done"), u = one("u"), t = one("t");
  const valid = !!u && !!t && verifyWeeklyMailToken(u, t);

  let body: React.ReactNode;
  if (done === "off") body = <Msg title="주간 메일을 더 보내지 않습니다" sub="검토함에서 언제든 다시 받을 수 있습니다." />;
  else if (done === "on") body = <Msg title="주간 메일을 다시 보냅니다" sub="저장한 회사에 새 공고가 있는 주에 월요일 아침 한 통입니다." />;
  else if (done === "bad") body = <Msg title="링크가 올바르지 않습니다" sub="메일에 있는 링크를 그대로 열거나, 로그인 뒤 검토함에서 바꿉니다." />;
  else if (done === "err") body = <Msg title="바꾸지 못했습니다" sub="잠시 뒤 다시 시도하거나 로그인 뒤 검토함에서 바꿉니다." />;
  else if (valid) body = (
    <form method="post" action="/api/mail/weekly" data-weekly-confirm className="flex flex-wrap items-center gap-3.5 pb-2.5 pt-[26px] text-[14.5px]">
      <input type="hidden" name="u" value={u} /><input type="hidden" name="t" value={t} /><input type="hidden" name="on" value="0" />
      <div>
        <b className="font-semibold text-ink">주간 메일을 그만 받습니까?</b>
        <span className="mt-1 block text-[13.5px] text-ink-dim">저장한 회사의 새 공고 메일(월요일 아침)이 더 가지 않습니다.</span>
      </div>
      <span className="grow" />
      <Btn variant="dark" type="submit">그만 받기</Btn>
    </form>
  );
  else body = <Msg title="링크가 올바르지 않습니다" sub="메일에 있는 링크를 그대로 열거나, 로그인 뒤 검토함에서 바꿉니다." />;

  return (
    <>
      <PageHead title="주간 메일" />
      <Panel className="mt-[22px]">{body}</Panel>
    </>
  );
}

function Msg({ title, sub }: { title: string; sub: string }) {
  return (
    <div data-weekly-done className="flex flex-wrap items-center gap-3.5 pb-2.5 pt-[26px] text-[14.5px]">
      <div>
        <b className="font-semibold text-ink">{title}</b>
        <span className="mt-1 block text-[13.5px] text-ink-dim">{sub}</span>
      </div>
      <span className="grow" />
      <Btn href="/saved">검토함</Btn>
    </div>
  );
}
