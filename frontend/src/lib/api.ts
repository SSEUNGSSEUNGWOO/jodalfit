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
  mode?: "company" | "keywords";
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

  try {
    const res = await fetch(`${API_BASE}/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
