// frontend/src/components/notice/ProposalInterest.tsx
// 공고 상세 레일 맨 아래 "제안서 작성 준비안 관심 등록" — 아직 없는 기능의 수요를 그 공고를 보고 있는 사람에게 묻는다(2026-11-05).
// 약속하지 않는다: "검토하고 있다 · 필요하면 관심 등록" 까지만. 누르면 /api/interest 에 register, 화면에 들어오면 view 를 한 번 보낸다.
// 날짜·범위·메일 안내는 적지 않는다 — 제공하기로 정할 때 별도 선택으로 받는다.
// 이름이 "초안"이 아니라 "작성 준비안"인 이유: 회사 맞춤 초안은 회사만 아는 실적·인력·차별점이 있어야 써지는데, 우리가 가진 건
// 제안요청서(첨부)뿐이다. 그걸로 되는 것 — 목차·평가항목 대응표·준비 자료 목록 — 만 묻는다. 초안이라 해 놓고 대부분을 사용자가
// 채우면 기대와 결과가 어긋난다(2026-11-05 외부 검토).
"use client";

import { useEffect, useRef, useState } from "react";
import { getSessionId } from "@/lib/analytics-session";

const FEATURE = "proposal_prep";

function post(event: "view" | "register", bidNtceNo: string, bidNtceOrd: string | null) {
  return fetch("/api/interest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feature: FEATURE, event, bidNtceNo, bidNtceOrd, sessionId: getSessionId() }),
  });
}

export function ProposalInterest({ bidNtceNo, bidNtceOrd }: { bidNtceNo: string; bidNtceOrd: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");

  // 노출은 탭·공고당 한 번 — 같은 페이지를 새로고침해도 분모가 늘지 않게 sessionStorage 로 막는다.
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const key = `jf_interest_view:${FEATURE}:${bidNtceNo}`;
    try { if (window.sessionStorage.getItem(key)) return; } catch { /* 저장소 막힘 — 그냥 보낸다 */ }
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      try { window.sessionStorage.setItem(key, "1"); } catch { /* 무시 */ }
      post("view", bidNtceNo, bidNtceOrd).catch(() => undefined);
    }, { threshold: 0.5 });
    io.observe(el);
    return () => io.disconnect();
  }, [bidNtceNo, bidNtceOrd]);

  async function register() {
    if (state === "sending" || state === "done") return;
    setState("sending");
    try {
      const r = await post("register", bidNtceNo, bidNtceOrd);
      setState(r.ok ? "done" : "error");
    } catch {
      setState("error");
    }
  }

  return (
    <div ref={ref} className="mt-5 border-t border-rule-2 pt-3" data-interest={FEATURE}>
      <span className="text-[12px] text-ink-g">제안서 작성 준비안 관심 등록</span>
      <p className="mt-1 text-[12.5px] leading-[1.6] text-ink">
        이 공고의 제안요청서를 바탕으로 목차·평가항목 대응표·준비 자료 목록을 정리하는 기능을 검토하고 있습니다. 필요하면 관심을 등록해 두시기 바랍니다.
      </p>
      {state === "done" ? (
        <p className="mt-2 text-[12.5px] leading-[1.6] text-ink" role="status">관심이 등록되었습니다. 기능 수요를 확인하는 데 참고합니다.</p>
      ) : (
        <button
          type="button"
          onClick={register}
          disabled={state === "sending"}
          className="mt-2 rounded-[4px] border border-orange px-3 py-1.5 text-[13px] font-[650] text-ink hover:text-orange-ink disabled:opacity-60"
        >
          관심 등록
        </button>
      )}
      {state === "error" && <p className="mt-1.5 text-[11.5px] text-ink-mute">등록이 되지 않았습니다. 잠시 뒤 다시 누르면 됩니다.</p>}
    </div>
  );
}
