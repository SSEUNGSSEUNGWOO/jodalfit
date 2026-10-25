// frontend/src/app/(renewal)/not-found.tsx
// 회사·공고 페이지가 notFound() 를 던질 때 — (renewal) 레이아웃(nav·바닥글) 안에서 같은 404 본문을 그린다.
import { NotFoundBlock } from "@/components/NotFoundBlock";

export default function NotFound() {
  return <NotFoundBlock />;
}
