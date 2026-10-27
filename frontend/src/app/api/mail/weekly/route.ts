// frontend/src/app/api/mail/weekly/route.ts
// 주간 메일 수신 여부 변경(POST) — 메일 하단 "그만 받기" 와 검토함 토글이 같은 폼을 보낸다.
// GET 만으로는 바꾸지 않는다(메일 보안 스캐너가 링크를 미리 열어도 해지되지 않게) — 페이지(page.tsx)가 확인 버튼을 보여주고 여기로 POST.
// 바꾸는 열은 0052 user_consents.marketing_opt_in 하나(lock 트리거가 허용하는 유일한 열). service_role 로 쓴다.
import { NextResponse } from "next/server";
import { verifyWeeklyMailToken } from "@/lib/mail-link";
import { getServerSupabase } from "@/lib/supabase-server";

export async function POST(req: Request) {
  const form = await req.formData();
  const u = String(form.get("u") ?? "");
  const t = String(form.get("t") ?? "");
  const on = String(form.get("on") ?? "") === "1";
  const back = String(form.get("back") ?? "");
  if (!verifyWeeklyMailToken(u, t)) return NextResponse.redirect(new URL("/mail/weekly?done=bad", req.url), 303);
  const { error } = await getServerSupabase().from("user_consents").update({ marketing_opt_in: on }).eq("user_id", u);
  if (error) return NextResponse.redirect(new URL("/mail/weekly?done=err", req.url), 303);
  const dest = back === "saved" ? "/saved" : `/mail/weekly?done=${on ? "on" : "off"}`;
  return NextResponse.redirect(new URL(dest, req.url), 303);
}
