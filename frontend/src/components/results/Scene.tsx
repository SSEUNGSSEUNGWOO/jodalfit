// 머리 장면 — 백엔드 funnel/stage 이벤트에 묶인 전진선. 관문 i 는 counts[i] 를 알아야 통과한다.
// 아직 모르면 관문 30px 앞에서 기다린다. 전부 알면 남은 구간을 짧게(구간당 260ms) 마무리한다. 클릭·Esc = 건너뛰기(settle).
"use client";

import { useEffect, useRef, useState } from "react";
import { createEngine, SCENE, type Engine } from "./scene-engine";
import { cn } from "@/lib/utils";

// 네 칸은 앞 칸의 부분집합이어야 한다 — 그래야 깔때기로 그려도 거짓이 아니다.
// "등록업종 허용 공고"(0056 의 845)를 둘째 칸으로 두던 건 거짓이었다: 후보 풀은 그 집합에서 꺼내는 게
// 아니라 전체 공고에서 유사도 순으로 뽑는다. 2026-10-23 확인(한종산업개발 최종 20건) — 업종 허용 9건 /
// 업종 제한 없음 3건 / 업종 불일치 8건. 그래서 둘째 칸을 후보 풀(candidates)로 바꾸고 0057 에서 그 수를 지웠다.
export const FUNNEL_LABELS = ["지금 입찰 가능한 공고", "비슷한 순서로 추린 공고", "참가 자격 통과 공고", "검토할 공고"] as const;
const REASONS = ["회사와 비슷하지 않음", "면허·지역 제한 미충족", "점수 순위에 밀림"] as const;

export type SceneCounts = {
  total: number | null;
  candidates: number | null;
  passed: number | null;
  results: number | null;
};

function subOf(c: SceneCounts, i: number): string {
  const pct = (a: number | null, b: number | null, d = 1) => (a != null && b ? `${((a / b) * 100).toFixed(d)}%` : "…");
  if (i === 0) return " · 마감 90일 이내";
  // 둘째 칸은 "왜 이만큼인가"가 숫자만으로 설명되지 않는다 — 전체의 몇 %인지 같이 적는다.
  if (i === 1) return ` · 전체의 ${pct(c.candidates, c.total)}`;
  if (i === 2)
    return c.passed === 0 ? " · 면허·지역 0% 통과" : ` · 앞 단계의 ${pct(c.passed, c.candidates, 0)}`;
  return c.results === 0 ? " · 없음" : ` · 앞 단계의 ${pct(c.results, c.passed)}`;
}

export function Scene({
  counts,
  playbackKey,
  state,
  onSettled,
}: {
  counts: SceneCounts;
  playbackKey: string;
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

  const cnt = [counts.total ?? -1, counts.candidates ?? -1, counts.passed ?? -1, counts.results ?? -1];
  const known = [counts.total != null, counts.candidates != null, counts.passed != null, counts.results != null];
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
    try {
      if (sessionStorage.getItem(`recommendation-scene:${playbackKey}`)) { finish(); return; }
    } catch { /* Optional playback memory. */ }
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
    if (settledRef.current || settled || state === "error") return;
    if (reduce) {
      if (target >= SCENE.W) finish();
      return;
    }
    let raf = 0,
      end = 0;
    let previous = performance.now();
    // 기다리는 동안은 천천히(0.22px/ms) — 계산을 덮는 시간이다. 숫자를 전부 알면 남은 거리를 1.2초 안에 마무리한다.
    // 결과가 이미 왔는데 일정 속도로 끝까지 가면 표가 5초 넘게 늦게 뜬다(2026-10-24 운영 실측: 응답 3초, 표 8.5초).
    const speed = target >= SCENE.W ? Math.max(0.22, (SCENE.W - xRef.current) / 1200) : 0.22;
    const tick = (now: number) => {
      const elapsed = Math.min(50, now - previous);
      previous = now;
      xRef.current = Math.min(target, xRef.current + elapsed * speed);
      eng.current?.paint(xRef.current);
      if (xRef.current < target) raf = requestAnimationFrame(tick);
      else if (target >= SCENE.W) end = window.setTimeout(finish, 450);
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
    try { sessionStorage.setItem(`recommendation-scene:${playbackKey}`, "1"); } catch { /* Optional playback memory. */ }
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
          // 라벨 한 줄 + 숫자 26px 가 들어가는 높이 — h-14(56) 에서는 숫자 아래가 잘렸다.
          done ? "h-0" : "h-[68px] max-sm:h-auto max-sm:grid max-sm:grid-cols-4 max-sm:gap-x-2.5 max-sm:py-2.5",
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
              "group/lab absolute top-1 opacity-0 transition-opacity duration-[400ms] max-sm:static",
              i > 0 && "border-l border-field pl-3 max-sm:border-0 max-sm:pl-0",
            )}
            style={{ left: `${(SCENE.XS[i] / SCENE.W) * 100}%` }}
          >
            {/* 390 은 네 칸이 한 줄이라 라벨 폭이 ~90px 다 — break-keep 이 없으면 "지금 입찰 가/능한 공고"로 단어 중간이 잘린다 */}
            <span className="block break-keep text-[12px] text-ink-g">{k}</span>
            <span
              className={cn(
                "num mt-[5px] block text-[26px] leading-[1.15] font-[650] tracking-[-0.04em] max-sm:text-[18px]",
                i === 3 ? "text-orange-ink" : "text-ink",
              )}
            >
              <span className="cnt" data-to={cnt[i]} />
              {/* 비율은 카운트업이 끝난 뒤에 — 세는 중에 "83 · 앞 단계의 45%"(최종 89 기준)처럼 어긋나 보였다 */}
              <small className="text-[11.5px] font-normal text-ink-mute opacity-0 transition-opacity duration-300 group-data-[full=true]/lab:opacity-100">{subOf(counts, i)}</small>
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
