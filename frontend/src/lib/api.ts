import type { RecommendationResponse } from "@/types/recommendations";
import { MOCK_RESPONSE } from "./mock-data";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const USE_MOCK =
  process.env.NEXT_PUBLIC_USE_MOCK === "true" ||
  (typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("mock") === "1");

export interface RecommendInput {
  query: string;
  mode?: "company" | "keywords" | "auto";
  limit?: number;
  candidate_pool?: number;
  with_explanation?: boolean;
}

export async function getRecommendations(
  input: RecommendInput
): Promise<RecommendationResponse> {
  if (USE_MOCK) {
    return new Promise((resolve) => setTimeout(() => resolve(MOCK_RESPONSE), 400));
  }

  // SSR 자체 호출(`node` UA + referer 없음)이 봇 차단에 걸리지 않도록 시크릿 토큰 첨부.
  // `NEXT_PUBLIC_` 접두 없이 = 서버 사이드에서만 읽힘. 클라이언트 번들엔 노출 X.
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (typeof window === "undefined" && process.env.INTERNAL_API_TOKEN) {
    headers["X-Internal-Token"] = process.env.INTERNAL_API_TOKEN;
  }

  try {
    const res = await fetch(`${API_BASE}/recommendations`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: input.query,
        mode: input.mode ?? "company",
        limit: input.limit ?? 5,
        candidate_pool: input.candidate_pool ?? 100,
        with_explanation: input.with_explanation ?? true,
      }),
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text();
      try {
        const data = JSON.parse(text);
        return {
          company: null,
          results: [],
          error: data.detail ?? data.error ?? `HTTP ${res.status}`,
        };
      } catch {
        return { company: null, results: [], error: `HTTP ${res.status}` };
      }
    }
    return (await res.json()) as RecommendationResponse;
  } catch (e) {
    return {
      company: null,
      results: [],
      error: (e as Error).message ?? "네트워크 오류",
    };
  }
}
