import { getRecommendations } from "@/lib/api";
import { fetchPeerRateByInstitution } from "@/lib/company";

// 회사 페이지 추천 섹션 전용. 추천(백엔드 10초 이상)을 SSR에서 빼서 크롤러가 받는
// HTML은 회사 정보만 담고, 사람이 페이지를 열면 브라우저가 여기로 요청한다.
// robots.txt가 /api/를 막으므로 크롤러는 이 경로를 타지 않는다.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ bizrno: string }> }
) {
  const { bizrno } = await params;
  if (!/^\d{10}$/.test(bizrno)) {
    return Response.json({ error: "invalid bizrno" }, { status: 400 });
  }

  const data = await getRecommendations({
    query: bizrno,
    mode: "company",
    limit: 20,
    with_explanation: false,
  });

  // 추천 TOP 5의 발주기관별 과거 평균 투찰율
  const top = data.results.slice(0, 5);
  const peerMap = data.error
    ? new Map()
    : await fetchPeerRateByInstitution(
        top.map((b) => b.dmnd_instt_nm).filter((x): x is string => !!x)
      );

  return Response.json({ data, peer: Object.fromEntries(peerMap) });
}
