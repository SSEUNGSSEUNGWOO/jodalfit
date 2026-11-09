// frontend/src/lib/suggested-company.ts
// 가입 직후 화면(/welcome·/consent)이 "방금 조회한 회사"를 한 번에 저장하게 — 돌아갈 주소(next)에서 회사를 읽는다(2026-11-09).
// 가입 버튼은 결과 화면의 로그인 판에서 눌리고 next 가 /recommendations?company=… 또는 /companies/<번호> 다. 그동안 그 회사를 알면서
// 빈 검색창에 이름을 다시 치게 했다. 저장 가능한 회사(벡터 있음·비공개 아님)만 돌려준다 — /api/saved/companies 가 같은 조건으로 404 를 낸다.
import "server-only";
import { EMB_COL } from "./embed-space";
import { fetchCompanyByBizrno } from "./company";
import { getServerSupabase } from "./supabase-server";
import type { SuggestedCompany } from "@/components/CompanySavePanel";

export type { SuggestedCompany };

export async function suggestedCompanyFromNext(next: string): Promise<SuggestedCompany | null> {
  const path = next.match(/^\/companies\/(\d{10})(?:[/?#]|$)/);
  const raw = path?.[1] ?? new URLSearchParams(next.split("?")[1] ?? "").get("company")?.trim();
  if (!raw) return null;
  const digits = raw.replace(/-/g, "");
  if (/^\d{10}$/.test(digits)) {
    const co = await fetchCompanyByBizrno(digits);
    if (!co || !co.has_embedding || co.optout_at) return null;
    return { bizrnoNorm: co.bizrno_norm, name: co.corp_nm };
  }
  if (raw.length > 50) return null;
  // 회사명으로 검색한 경우 — 정확히 같은 이름(계약 많은 행). 오타·부분 일치는 추정하지 않는다(검색창이 받는다).
  const { data } = await getServerSupabase()
    .from("companies")
    .select("bizrno_norm,corp_nm")
    .eq("corp_nm", raw)
    .is("optout_at", null)
    .not(EMB_COL, "is", null)
    .order("contract_count", { ascending: false, nullsFirst: false })
    .limit(1)
    .maybeSingle();
  return data ? { bizrnoNorm: data.bizrno_norm, name: data.corp_nm } : null;
}
