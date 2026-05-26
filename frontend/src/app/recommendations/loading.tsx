"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const STAGES: { atMs: number; title: string; sub: string }[] = [
  { atMs: 0, title: "회사 정보 매칭 중...", sub: "보통 5~12초 걸려요" },
  { atMs: 1500, title: "공고 218,435건과 벡터 비교 중...", sub: "회사 정체성과 가장 가까운 공고를 찾는 중" },
  { atMs: 3500, title: "매칭 시그널 분석 중...", sub: "거래 기관·등록업종·체급 일치 검사" },
  { atMs: 6000, title: "AI가 추천 이유 작성 중...", sub: "공고마다 매칭 근거를 한 줄로 정리하는 중" },
  { atMs: 10000, title: "거의 완료되었어요", sub: "응답을 정리하는 중" },
];

const ETA_MS = 12000;

export default function Loading() {
  const [stage, setStage] = useState(0);
  const [progress, setProgress] = useState(2);

  useEffect(() => {
    const start = performance.now();
    const tick = () => {
      const elapsed = performance.now() - start;
      const next = STAGES.findLastIndex((s) => elapsed >= s.atMs);
      setStage(next >= 0 ? next : 0);
      // 비선형 — 처음 4초 빠르게 60%, 그 후 천천히 95%까지
      const pct = elapsed < 4000
        ? (elapsed / 4000) * 60
        : 60 + Math.min(35, ((elapsed - 4000) / (ETA_MS - 4000)) * 35);
      setProgress(Math.max(2, Math.min(95, pct)));
    };
    tick();
    const id = setInterval(tick, 200);
    return () => clearInterval(id);
  }, []);

  const current = STAGES[stage];

  return (
    <>
      <Header />
      <main className="flex-1">
        <div className="mx-auto max-w-[640px] px-5 py-24 sm:py-28 text-center">
          <Loader2 className="mx-auto h-7 w-7 animate-spin text-brand" aria-hidden />
          <p className="mt-6 text-[15.5px] text-ink-3 transition-opacity duration-300">
            {current.title}
          </p>
          <p className="mt-1.5 text-[12.5px] text-ink-5 transition-opacity duration-300">
            {current.sub}
          </p>
          <div
            className="mx-auto mt-5 h-1 w-48 overflow-hidden rounded-full bg-ink-7/60"
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-brand transition-[width] duration-200 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
