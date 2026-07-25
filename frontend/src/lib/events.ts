"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const SID_KEY = "jf_sid";

export function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let sid = window.sessionStorage.getItem(SID_KEY);
    if (!sid) {
      sid = crypto.randomUUID();
      window.sessionStorage.setItem(SID_KEY, sid);
    }
    return sid;
  } catch {
    return null;
  }
}

export interface NoticeEventPayload {
  event_type: "click" | "save" | "dismiss" | "subscribe";
  bid_ntce_no: string;
  bid_ntce_ord?: string;
  target_bizrno?: string | null;
  rank_position?: number;
  algorithm_version?: string;
  score?: number;
}

/** fire-and-forget — 페이지 이탈 중에도 전송되도록 keepalive */
export function emitNoticeEvent(payload: NoticeEventPayload): void {
  try {
    void fetch(`${API_BASE}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, session_id: getSessionId() }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    // 로깅 실패는 무시
  }
}
