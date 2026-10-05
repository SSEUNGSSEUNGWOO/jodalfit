import { fetchSimilarNotices } from "@/lib/notice";

// 공고 상세 "비슷한 공고" 전용. "오늘 이후 마감"으로 거르는 결과를 ISR 캐시 HTML에서 빼서
// 공고 페이지가 날짜 때문에 매일 다시 쓰이지 않게 한다 — 사람이 페이지를 열면 브라우저가 여기로 요청한다.
// s-maxage로 CDN이 공고별 응답을 1시간 들고 있으므로 함수 호출은 공고당 시간당 1번 수준이다.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ bid_ntce_no: string }> }
) {
  const { bid_ntce_no } = await params;
  if (!/^[A-Za-z0-9_-]{1,40}$/.test(bid_ntce_no)) {
    return Response.json({ error: "invalid bid_ntce_no" }, { status: 400 });
  }
  const similar = await fetchSimilarNotices(bid_ntce_no, 10);
  return Response.json(similar, {
    headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" },
  });
}
