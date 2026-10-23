// 머리 장면 — 백엔드 funnel/stage 이벤트에 묶인 전진선. 관문 i 는 counts[i] 를 알아야 통과한다.
// 아직 모르면 관문 30px 앞에서 기다린다. 전부 알면 남은 구간을 짧게(구간당 260ms) 마무리한다. 클릭·Esc = 건너뛰기(settle).
"use client";

import { useEffect, useRef, useState } from "react";
import { createEngine, SCENE, type Engine } from "./scene-engine";
import { cn } from "@/lib/utils";

export const FUNNEL_LABELS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "참가 자격 통과 공고", "검토할 공고"] as const;
const REASONS = ["등록업종 미허용", "면허·지역 제한 미충족", "회사와의 유사도 낮음"] as const;

export type SceneCounts = {
  total: number | null;
  industry: number | null;
  candidates: number | null;
  passed: number | null;
  results: number | null;
};

function subOf(c: SceneCounts, i: number): string {
  const pct = (a: number | null, b: number | null, d = 1) => (a != null && b ? `${((a / b) * 100).toFixed(d)}%` : "…");
  if (i === 0) return " · 마감 90일 이내";
  if (i === 1) return ` · 전체의 ${pct(c.industry, c.total)}`;
  if (i === 2)
    return c.passed === 0 ? " · 면허·지역 0% 통과" : ` · 후보 ${c.candidates ?? "…"}건 중 ${pct(c.passed, c.candidates, 0)} 통과`;
  return c.results === 0 ? " · 없음" : ` · 앞 단계의 ${pct(c.results, c.passed)}`;
}

export function Scene({
  counts,
  state,
  onSettled,
}: {
  counts: SceneCounts;
  state: "running" | "done" | "error";
  onSettled: () => void;
}) {
  const cv = useRef<HTMLCanvasElement>(null);
  const labs = useRef<(HTMLDivElement | null)[]>([]);
  const rsns = useRef<(HTMLSpanElement | null)[]>([]);
  const eng = useRef<Engine | null>(null);
  const xRef = useRef(0);
  const settledRef = useRef(false); // onSettled 는 한 번만 — 상태는 렌더용
  const [settled, setSettled] = useState(false);
  const reduce = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

  const cnt = [counts.total ?? -1, counts.industry ?? -1, counts.passed ?? -1, counts.results ?? -1];
  const known = [counts.total != null, counts.industry != null, counts.passed != null, counts.results != null];
  const firstUnknown = known.findIndex((k) => !k);
  // results 를 알면 종점이다 — 0056 미적용·v1 경로면 앞 칸이 비어도 선은 끝까지 간다(라벨은 "…" 유지).
  const target =
    state === "error"
      ? Math.min(xRef.current, SCENE.XS[3] - 30)
      : counts.results != null || firstUnknown < 0
        ? SCENE.W
        : // 0번 칸 앞에는 벽이 없다 — 숫자를 몰라도 1번 벽까지는 간다(선 개수는 기하 기본값, 라벨은 "…").
          SCENE.XS[Math.max(1, firstUnknown)] - 30;

  useEffect(() => {
    if (!cv.current) return;
    const e = createEngine(
      cv.current,
      labs.current.filter(Boolean) as HTMLElement[],
      rsns.current.filter(Boolean) as HTMLElement[],
      cnt,
    );
    eng.current = e;
    e.setup();
    e.paint(0);
    const onResize = () => {
      e.setup();
      e.paint(xRef.current);
    };
    addEventListener("resize", onResize);
    return () => removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    eng.current?.setCounts(cnt);
    eng.current?.paint(xRef.current);
  }, [cnt.join(","), settled]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (settled || state === "error") return;
    if (reduce) {
      if (target >= SCENE.W) finish();
      return;
    }
    let raf = 0,
      end = 0;
    const from = xRef.current,
      t0 = performance.now();
    const dist = Math.max(0, target - from);
    const dur = Math.max(1, dist / 288) * 260;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      xRef.current = from + dist * (1 - Math.pow(1 - p, 2.2));
      eng.current?.paint(xRef.current);
      if (p < 1) raf = requestAnimationFrame(tick);
      else if (target >= SCENE.W) end = window.setTimeout(finish, 150);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(end); // 오류로 넘어간 뒤 장면을 접지 않도록
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, settled, state]);

  function finish() {
    if (settledRef.current || state === "error") return;
    settledRef.current = true;
    xRef.current = SCENE.W;
    eng.current?.paint(SCENE.W);
    setSettled(true);
    onSettled();
  }
  function skip() {
    if (state !== "error") finish();
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skip();
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled, state]);

  const done = settled && state !== "error";
  return (
    <div
      data-scene
      data-done={done}
      className={cn("mt-5 border-t border-ink", !done && state !== "error" && "cursor-pointer")}
      onClick={skip}
      aria-hidden="true"
    >
      <div
        className={cn(
          "relative overflow-hidden transition-[height] duration-500 [transition-timing-function:var(--ease-sheet)]",
          done ? "h-0" : "h-14 max-sm:h-auto max-sm:grid max-sm:grid-cols-4 max-sm:gap-x-2.5 max-sm:py-2.5",
        )}
      >
        {FUNNEL_LABELS.map((k, i) => (
          <div
            key={k}
            ref={(el) => {
              labs.current[i] = el;
            }}
            data-x={SCENE.XS[i]}
            data-lab
            className={cn(
              "absolute top-1 opacity-0 transition-opacity duration-[400ms] max-sm:static",
              i > 0 && "border-l border-field pl-3 max-sm:border-0 max-sm:pl-0",
            )}
            style={{ left: `${(SCENE.XS[i] / SCENE.W) * 100}%` }}
          >
            <span className="block text-[12px] text-ink-g">{k}</span>
            <span
              className={cn(
                "num mt-[5px] block text-[26px] font-[650] tracking-[-0.04em] max-sm:text-[18px]",
                i === 3 ? "text-orange" : "text-ink",
              )}
            >
              <span className="cnt" data-to={cnt[i]} />
              <small className="text-[11.5px] font-normal text-ink-mute">{subOf(counts, i)}</small>
            </span>
          </div>
        ))}
      </div>
      <div
        className={cn(
          "relative overflow-hidden transition-[height] duration-[550ms] [transition-timing-function:var(--ease-sheet)]",
          done ? "h-0" : "h-[392px] max-sm:h-[220px]",
        )}
      >
        <canvas
          ref={cv}
          height={SCENE.H}
          className={cn(
            "block h-[392px] w-full transition-transform duration-[550ms] max-sm:h-[220px]",
            done && "-translate-y-[150px]",
          )}
        />
        {REASONS.map((r, i) => (
          <span
            key={r}
            ref={(el) => {
              rsns.current[i] = el;
            }}
            data-x={SCENE.XS[i + 1] + 14}
            data-rsn={i + 1}
            className={cn(
              "absolute bg-paper px-[5px] py-px text-[11.5px] text-ink-g opacity-0 transition-opacity duration-[400ms] max-sm:hidden",
              i === 2 && counts.passed === 0 && "hidden",
            )}
            style={{ right: `${100 - (SCENE.XS[i + 1] / SCENE.W) * 100}%`, top: SCENE.RSN_Y, marginRight: 8 }}
          >
            {r}
          </span>
        ))}
      </div>
    </div>
  );
}
