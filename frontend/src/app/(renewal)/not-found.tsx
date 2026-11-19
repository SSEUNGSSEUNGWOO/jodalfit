// frontend/src/app/(renewal)/not-found.tsx
// 404 — 리뉴얼 레이아웃 안에서 notFound() 가 불릴 때(회사·공고 없음). nav·footer 는 레이아웃이 준다.
// 비공개 요청 회사(0037)는 "없는 페이지"가 아니라 "회사 요청으로 비공개"라고 적는다(2026-11-19). 상태는 그대로 404, 상호는 싣지 않는다.
import { headers } from "next/headers";
import { NotFoundBlock } from "@/components/NotFoundBlock";
import { fetchOptoutBizrnos } from "@/lib/optout";

export default async function NotFound() {
  const m = ((await headers()).get("x-pathname") ?? "").match(/^\/companies\/([^/]+)\/?$/);   // proxy.ts 가 넣는다
  const norm = m ? m[1].replace(/\D/g, "") : "";
  const optout = norm.length === 10 && (await fetchOptoutBizrnos().catch(() => new Set<string>())).has(norm);
  return <NotFoundBlock optout={optout} />;
}
