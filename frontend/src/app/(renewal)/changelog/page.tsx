// 공개용 개선 안내만 렌더링한다. 내부 실험 문서는 읽거나 화면으로 전달하지 않는다.
import type { Metadata } from "next";
import { getChangelog } from "@/lib/changelog";

export const metadata: Metadata = {
  title: "서비스 개선 기록 | 조달핏",
  description: "조달핏의 검색·추천·검토함에서 달라진 기능과 이용에 도움이 되는 개선 사항을 안내합니다.",
  alternates: { canonical: "/changelog" },
};

export default async function ChangelogPage() {
  const log = await getChangelog();
  return (
    <div className="mx-auto max-w-[840px] pb-20">
      <header className="mt-10 border-b border-ink pb-5 max-sm:mt-6">
        <h1 className="text-[28px] font-[650] tracking-[-0.03em] text-ink max-sm:text-[22px]">서비스 개선 기록</h1>
        <p className="mt-3 text-[14px] leading-[1.75] text-ink-g">검색·추천·검토함에서 달라진 기능과 이용에 도움이 되는 개선 사항을 안내합니다.</p>
        {log.lastDate && <p className="mt-2 text-[12.5px] text-ink-mute">최근 업데이트 {log.lastDate.replace(/-/g, ".")} · 변경 {log.entries.length}건</p>}
      </header>
      <section className="mt-7" aria-label="개선 사항">
        {log.entries.map((e) => (
          <article key={`${e.date}-${e.title}`} className="grid grid-cols-[112px_minmax(0,1fr)] gap-x-6 border-t border-rule py-6 max-sm:grid-cols-1 max-sm:gap-y-1.5">
            <time dateTime={e.date} className="num pt-0.5 text-[13px] text-ink-g">{e.date.replace(/-/g, ".")}</time>
            <div>
              <h2 className="text-[15.5px] font-[650] leading-[1.45] text-ink">{e.title}</h2>
              {e.changes.map((text) => <p key={text} className="mt-2.5 text-[14px] leading-[1.75] text-ink-g">{text}</p>)}
            </div>
          </article>
        ))}
      </section>
      <p className="mt-6 border-t border-rule pt-4 text-[13px] leading-[1.7] text-ink-g">
        추천 기준과 확인이 필요한 조건은 <a href="/about#how-we-pick" className="border-b border-field text-ink hover:border-orange">서비스 소개</a>에서 확인할 수 있습니다.
        추천은 검토 순서이며 낙찰 가능성을 예측하지 않습니다. 입찰 전 공고 원문과 참가 자격을 확인해야 합니다.
      </p>
    </div>
  );
}
