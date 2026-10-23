// frontend/src/app/(renewal)/changelog/page.tsx
// 개선 기록(08) — "무엇을 바꿨고 그래서 얼마나 나아졌나".
// 원천은 docs/recommender/changelog.md 하나다(lib/changelog.ts). 화면용 사본을 두지 않는다.
// 본문은 토큰을 React 요소로 그린다 — HTML 문자열을 만들지 않는다.
import type { Metadata } from "next";
import { getChangelog, type Block, type ChangeEntry, type Tok } from "@/lib/changelog";
import { getEntryData } from "@/lib/entry";
import { NEGATIVE, NOTE, POSITIVE, steps } from "@/lib/how-we-pick";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "추천 품질 개선 기록 | 조달핏",
  description: "조달핏이 공고를 어떻게 고르는지, 무엇을 바꿨고 그래서 얼마나 나아졌는지를 같은 방법으로 재서 적습니다.",
  alternates: { canonical: "/changelog" },
};

// 레포 파일을 읽으므로 캐시가 오래 남으면 안 된다. 한 시간마다 다시 읽는다.
export const revalidate = 3600;

function Rich({ toks }: { toks: Tok[] }) {
  return (
    <>
      {toks.map((k, i) =>
        k.b ? (
          <b key={i} className="font-[650] text-ink">{k.t}</b>
        ) : k.c ? (
          <code key={i} className="rounded-[3px] bg-rule-2 px-1 py-px text-[12.5px]">{k.t}</code>
        ) : (
          <span key={i}>{k.t}</span>
        ),
      )}
    </>
  );
}

function Blocks({ blocks }: { blocks: Block[] }) {
  return (
    <>
      {blocks.map((b, i) => {
        if (b.kind === "p")
          return (
            <p key={i} className="mt-2.5 text-[14px] leading-[1.75] text-ink-g">
              <Rich toks={b.toks} />
            </p>
          );
        if (b.kind === "ul")
          return (
            <ul key={i} className="mt-2.5 list-disc pl-5 text-[14px] leading-[1.75] text-ink-g marker:text-ink-mute">
              {b.items.map((t, j) => (
                <li key={j}>
                  <Rich toks={t} />
                </li>
              ))}
            </ul>
          );
        return (
          <div key={i} className="mt-3 overflow-x-auto">
            <table className="w-full border-collapse text-[13.5px]">
              <thead>
                <tr>
                  {b.head.map((h, j) => (
                    <th key={j} className="border-b border-ink px-2 py-1.5 text-left font-[650] text-ink">
                      <Rich toks={h} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {b.rows.map((r, j) => (
                  <tr key={j}>
                    {r.map((c, k) => (
                      <td key={k} className={cn("num border-b border-rule px-2 py-1.5 text-ink-g", k === 0 && "text-ink")}>
                        <Rich toks={c} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </>
  );
}

function Entry({ e }: { e: ChangeEntry }) {
  return (
    <article className="grid grid-cols-[112px_minmax(0,1fr)] gap-x-6 border-t border-rule py-6 max-sm:grid-cols-1 max-sm:gap-y-1.5">
      <div className="pt-0.5">
        <div className="num text-[13px] text-ink-g">{e.date?.replace(/-/g, ".")}</div>
        {e.tag && (
          <span
            className={cn(
              "mt-1 inline-block rounded-full border px-2 py-0.5 text-[11.5px]",
              e.tag === "처음 측정" ? "border-orange text-orange" : "border-field text-ink-mute",
            )}
          >
            {e.tag}
          </span>
        )}
      </div>
      <div>
        <h3 className="text-[15.5px] font-[650] leading-[1.45] text-ink">{e.title}</h3>
        <Blocks blocks={e.blocks} />
      </div>
    </article>
  );
}

export default async function ChangelogPage() {
  const [log, entry] = await Promise.all([getChangelog(), getEntryData().catch(() => null)]);
  const active = entry?.active ?? 0;

  return (
    <div className="mx-auto max-w-[840px] pb-20">
      <header className="mt-10 border-b border-ink pb-5 max-sm:mt-6">
        <h1 className="text-[28px] font-[650] tracking-[-0.03em] text-ink max-sm:text-[22px]">추천 품질 개선 기록</h1>
        {log.lead.map((t, i) => (
          <p key={i} className="mt-3 text-[14px] leading-[1.75] text-ink-g">
            <Rich toks={t} />
          </p>
        ))}
      </header>

      {/* 지금 — 문서의 '지금' 항목 그대로. 표(처음/지금)와 다음 병목이 들어 있다. */}
      {log.now && (
        <section className="mt-7 rounded-[6px] border border-hair bg-panel px-6 py-5 max-sm:px-4">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-[16px] font-[650] text-ink">{log.now.title}</h2>
            <span className="text-[12.5px] text-ink-mute">
              변경 {log.entries.length}건 · 마지막 {log.lastDate?.slice(5).replace("-", ".")}
            </span>
          </div>
          <Blocks blocks={log.now.blocks} />
        </section>
      )}

      {/* 어떻게 고르는가 — 단계는 구조, 점수표는 운영 코드 값(lib/how-we-pick.ts) */}
      {active > 0 && (
        <section className="mt-6 rounded-[6px] border border-hair bg-panel px-6 py-5 max-sm:px-4">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-[16px] font-[650] text-ink">어떻게 고르는가</h2>
            <span className="text-[12.5px] text-ink-mute">점수표는 운영 코드 값 · 회사별 실제 수치는 결과 화면에</span>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-5 max-sm:grid-cols-2">
            {steps(active).map((s) => (
              <div key={s.k}>
                <div className="num text-[22px] font-[650] tracking-[-0.03em] text-ink">{s.n}</div>
                <div className="mt-0.5 text-[13px] font-[650] text-ink">{s.k}</div>
                <p className="mt-1 text-[12.5px] leading-[1.6] text-ink-g">{s.d}</p>
                <p className="mt-1 text-[12px] text-ink-mute">{s.sub}</p>
              </div>
            ))}
          </div>
          <div className="mt-5 grid grid-cols-2 gap-6 border-t border-rule pt-4 max-sm:grid-cols-1">
            {[
              { k: "점수를 올리는 것", rows: POSITIVE },
              { k: "점수를 내리는 것", rows: NEGATIVE },
            ].map((g) => (
              <div key={g.k}>
                <span className="text-[12.5px] text-ink-g">{g.k}</span>
                <ul className="mt-1.5">
                  {g.rows.map((f) => (
                    <li key={f.t} className="flex items-baseline justify-between gap-3 border-b border-rule-2 py-1.5 text-[13.5px]">
                      <span className="text-ink-g">
                        {f.t}
                        {f.d && <span className="ml-1.5 text-[12px] text-ink-mute">{f.d}</span>}
                      </span>
                      <b className={cn("num shrink-0 font-[650]", f.v.startsWith("−") ? "text-ink-mute" : "text-ink")}>{f.v}</b>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[12.5px] leading-[1.7] text-ink-mute">{NOTE}</p>
        </section>
      )}

      <section className="mt-8">
        {log.entries.map((e) => (
          <Entry key={`${e.date}-${e.title}`} e={e} />
        ))}
      </section>

      <p className="mt-6 border-t border-rule pt-4 text-[12.5px] leading-[1.7] text-ink-mute">
        내부 작업 {log.hidden}건은 화면에서 숨겼습니다(원문에는 있습니다). 채점표가 생긴 2026-10-13 이전 항목은 전후 수치가 없어
        &quot;측정 전&quot;으로 표시합니다.
      </p>
    </div>
  );
}
