// frontend/src/components/results/HelpfulLine.tsx
// 결과 화면 맨 아래 한 줄 — "이 결과가 검토에 도움이 됐습니까?" 예/아니오(+아니오면 한 줄 메모).
// 추천 품질을 사용자 쪽에서 재는 유일한 수단(2026-10-27). 백엔드 POST /events/helpful → 0063 result_feedback, /admin 응답 건강 판.
// 같은 탭에서 같은 질의에는 다시 묻지 않는다(sessionStorage).
"use client";

import { useState } from "react";
import { Btn } from "@/components/Btn";
import { track } from "@/lib/analytics";
import { getSessionId } from "@/lib/events";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function HelpfulLine({ mode, query, bizrno }: { mode: "company" | "keywords"; query: string; bizrno: string | null }) {
  const key = `jf:helpful:${mode}:${query}`;
  // 결과 판은 계산이 끝난 뒤 브라우저에서만 그려지므로 저장소를 바로 읽어도 서버 렌더와 어긋나지 않는다.
  const [state, setState] = useState<"ask" | "no" | "done">(() => { try { return sessionStorage.getItem(key) ? "done" : "ask"; } catch { return "ask"; } });
  const [note, setNote] = useState("");

  function send(helpful: boolean, text?: string) {
    track("result_helpful", { mode, helpful: helpful ? 1 : 0, with_note: text ? 1 : 0 });
    try {
      void fetch(`${API_BASE}/events/helpful`, {
        method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
        body: JSON.stringify({ mode, query: query.slice(0, 200), bizrno_norm: bizrno, helpful, note: text?.slice(0, 300) || null, session_id: getSessionId() }),
      }).catch(() => {});
    } catch { /* 기록 실패는 무시 */ }
    try { sessionStorage.setItem(key, "1"); } catch { /* 저장소 막힘 — 다음에 다시 물을 뿐 */ }
  }

  return (
    <div data-helpful data-state={state} className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2.5 border-t border-hair pt-4 text-[13.5px] text-ink">
      {state === "done" ? (
        <span className="text-ink-g">고맙습니다. 추천을 고치는 데 씁니다.</span>
      ) : state === "no" ? (
        <form className="flex w-full flex-wrap items-center gap-2.5" onSubmit={(e) => { e.preventDefault(); send(false, note); setState("done"); }}>
          <label htmlFor="helpful-note" className="text-ink-g">무엇이 아쉬웠습니까 (선택)</label>
          <input id="helpful-note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} autoFocus
            placeholder="예: 우리 업종과 다른 공고가 많다" className="h-9 min-w-0 flex-1 rounded-[6px] border border-field bg-panel px-3 text-[13.5px] text-ink outline-none placeholder:text-ink-mute focus:border-ink" />
          <Btn variant="dark" type="submit" className="h-9">보내기</Btn>
          <button type="button" className="cursor-pointer border-b border-field text-[13px] text-ink-g hover:border-orange" onClick={() => { send(false); setState("done"); }}>건너뛰기</button>
        </form>
      ) : (
        <>
          <span>이 결과가 검토에 도움이 됐습니까?</span>
          <span className="flex gap-2">
            <Btn className="h-8 px-3 text-[13px]" onClick={() => { send(true); setState("done"); }}>예</Btn>
            <Btn className="h-8 px-3 text-[13px]" onClick={() => setState("no")}>아니오</Btn>
          </span>
        </>
      )}
    </div>
  );
}
