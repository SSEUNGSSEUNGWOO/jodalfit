// frontend/src/app/opengraph-image.tsx
// 공유 카드(1200×630). 09 전환에서 리뉴얼 색·문구로.
//
// 색 규칙(docs/design/brand/README.md): 종이 #faf9f7 · 먹 #141414 · 주황 #f97316.
// **주황은 선이지 면이 아니다.** 유일한 예외가 로고 타일(주황 면 + 흰 마크)이라 여기서도 타일만 면이다.
// 문구: "TOP 5" 는 안 쓴다 — 지금은 20건을 보여주고, 숫자를 박으면 또 어긋난다.
import { ImageResponse } from "next/og";
import { loadPretendard, ogFonts } from "./_og/fonts";

export const alt = "조달핏 — 우리 회사가 검토할 만한 입찰공고";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PAPER = "#faf9f7";
const INK = "#141414";
const GREY = "#55554f";
const ORANGE = "#f97316";
const HAIR = "#e6e4df";

export default async function Image() {
  const fonts = await loadPretendard();
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: PAPER,
          fontFamily: "Pretendard",
          padding: "72px 80px",
        }}
      >
        {/* 로고 락업 — 주황 타일 + 흰 마크. 타일이 유일하게 허용된 주황 면이다. */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <svg width="56" height="56" viewBox="0 0 64 64">
            <rect width="64" height="64" rx="14.08" fill={ORANGE} />
            <path d="M30 14 H50 V34 M14 30 V50 H34" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div style={{ display: "flex", fontSize: 38, fontWeight: 800, letterSpacing: "-0.035em", color: INK }}>조달핏</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 68, fontWeight: 700, letterSpacing: "-0.03em", color: INK, lineHeight: 1.25 }}>
            우리 회사가 검토할 만한
          </div>
          <div style={{ display: "flex", fontSize: 68, fontWeight: 700, letterSpacing: "-0.03em", color: INK, lineHeight: 1.25 }}>
            입찰공고만 추립니다
          </div>
          <div style={{ display: "flex", marginTop: 22, fontSize: 28, fontWeight: 500, color: GREY, lineHeight: 1.5 }}>
            등록업종 · 공급물품 · 수주 이력으로 찾습니다. 낙찰을 예측하지 않습니다.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderTop: `1px solid ${HAIR}`,
            paddingTop: 24,
            fontSize: 22,
            color: GREY,
            fontWeight: 500,
          }}
        >
          <div style={{ display: "flex" }}>나라장터 공공데이터 기반 · 매일 05:00 갱신</div>
          <div style={{ display: "flex", color: INK, fontWeight: 700 }}>jodalfit.co.kr</div>
        </div>
      </div>
    ),
    { ...size, fonts: ogFonts(fonts) },
  );
}
