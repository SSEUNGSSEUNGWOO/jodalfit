// frontend/src/app/api/interest/route.ts
// 미출시 기능 수요 조사 기록(0068 feature_interest) — 공고 상세 "제안서 작성 준비안 관심 등록".
// view = 버튼이 화면에 들어옴(분모), register = 클릭. 로그인 사용자는 user_id 로 한 번만(23505 는 이미 등록), 비로그인은 user_id null 로 따로.
// 봇 UA 는 기록하지 않고 ok 만 돌려준다 — 서버 렌더의 97% 가 크롤러라 분모가 부풀면 클릭률이 0 에 가깝게 보인다.
import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth";
import { getServerSupabase } from "@/lib/supabase-server";

const FEATURES = new Set(["proposal_prep"]);
const BOT_UA = /bot|crawl|spider|headless|meta-externalagent|slurp|yeti|python-requests|node/i;

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as
    | { feature?: unknown; event?: unknown; bidNtceNo?: unknown; bidNtceOrd?: unknown; sessionId?: unknown }
    | null;
  const feature = typeof body?.feature === "string" ? body.feature : "proposal_prep";
  const event = body?.event === "view" || body?.event === "register" ? body.event : null;
  const bidNtceNo = typeof body?.bidNtceNo === "string" ? body.bidNtceNo.trim() : "";
  const bidNtceOrd = typeof body?.bidNtceOrd === "string" ? body.bidNtceOrd.slice(0, 10) : null;
  const sessionId = typeof body?.sessionId === "string" ? body.sessionId.slice(0, 64) : null;
  if (!FEATURES.has(feature) || !event || !/^[A-Z0-9]{5,30}$/i.test(bidNtceNo)) {
    return NextResponse.json({ error: "bad" }, { status: 400 });
  }
  const ua = (req.headers.get("user-agent") ?? "").slice(0, 300);
  if (!ua || BOT_UA.test(ua)) return NextResponse.json({ ok: true, skipped: true }, { headers: { "Cache-Control": "no-store" } });

  const user = await getSessionUser();
  const { error } = await getServerSupabase().from("feature_interest").insert({
    feature,
    event,
    bid_ntce_no: bidNtceNo,
    bid_ntce_ord: bidNtceOrd,
    user_id: user?.id ?? null,
    session_id: sessionId,
    user_agent: ua,
  });
  if (error && error.code !== "23505") return NextResponse.json({ error: "db" }, { status: 500 });
  return NextResponse.json({ ok: true, signedIn: !!user }, { headers: { "Cache-Control": "no-store" } });
}
