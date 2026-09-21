import "server-only";
import { getServerSupabase } from "./supabase-server";

/** 비공개 요청 회사의 bizrno_norm 집합 (migration 0037).
 *
 *  sitemap_urls·industry_companies MV 정의에 이 필터를 넣으려면 MV 를 drop→create→
 *  refresh 해야 하는데, 회사 6만 행 기준 10분 넘게 ACCESS EXCLUSIVE 락을 잡아
 *  그동안 사이트맵 라우트가 500 을 낸다 (2026-09-21 실측). 비공개 요청은 건수가
 *  매우 적으므로 MV 를 읽는 쪽에서 걸러낸다.
 */
export async function fetchOptoutBizrnos(): Promise<Set<string>> {
  const { data } = await getServerSupabase()
    .from("companies")
    .select("bizrno_norm")
    .not("optout_at", "is", null);
  return new Set(
    ((data as { bizrno_norm: string | null }[]) ?? [])
      .map((r) => r.bizrno_norm)
      .filter((v): v is string => !!v)
  );
}
