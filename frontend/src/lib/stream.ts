// frontend/src/lib/stream.ts
// POST /recommendations/stream (NDJSON) 을 이벤트로. 브라우저에서 백엔드로 직접(옛 BoardView 와 같은 경로).
import type { StreamEvent } from "@/types/recommendations";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type StreamBody = {
  query: string; mode: "company" | "keywords"; keywords?: string | null; algorithm: "v1" | "v2";
  session_id?: string | null; limit: number; candidate_pool: number; explain_top: number; with_explanation: boolean;
  div?: string | null; due?: number | null;   // 키워드 모드 좁히기(구분·마감까지 일수)
};

/** 이벤트마다 onEvent. 네트워크/HTTP 오류는 throw — 호출자가 오류 상태로 바꾼다. */
export async function streamRecommendations(body: StreamBody, onEvent: (e: StreamEvent) => void, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${API_BASE}/recommendations/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  });
  if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try { onEvent(JSON.parse(line) as StreamEvent); } catch { /* 깨진 줄은 버린다 */ }
    }
  }
  if (buf.trim()) { try { onEvent(JSON.parse(buf) as StreamEvent); } catch { /* ignore */ } }
}
