// frontend/src/app/apple-icon.tsx
// iOS 홈 화면 아이콘(180×180 PNG). SVG 로는 안 된다 — 사파리가 apple-touch-icon 에서 SVG 를 안 읽는다.
// 자산 원본은 docs/design/brand/tile.svg (주황 타일 + 흰 마크). 타일은 브랜드 규칙이 허용한
// 유일한 주황 '면'이다(docs/design/brand/README.md).
import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%" }}>
        <svg width="180" height="180" viewBox="0 0 64 64">
          <rect width="64" height="64" rx="14.08" fill="#f97316" />
          <path d="M30 14 H50 V34 M14 30 V50 H34" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    ),
    size,
  );
}
