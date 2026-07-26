import { ImageResponse } from "next/og";
import { loadPretendard, ogFonts } from "./_og/fonts";

export const alt = "jodalfit — 우리 회사가 검토할 만한 공공입찰";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PRIMARY = "#047857";
const INK = "#111827";
const MUTED = "#6B7280";
const BORDER = "#E5E7EB";

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
          background: "#FFFFFF",
          fontFamily: "Pretendard",
          padding: "72px 80px",
          position: "relative",
        }}
      >
        {/* 우상단 장식 - Halves 모티프 */}
        <div
          style={{
            position: "absolute",
            top: 72,
            right: 80,
            width: 88,
            height: 88,
            display: "flex",
          }}
        >
          <svg width="88" height="88" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg">
            <polygon points="0,0 88,0 0,88" fill={PRIMARY} />
            <polygon points="88,88 88,0 0,88" fill="none" stroke={PRIMARY} strokeWidth="4" />
          </svg>
        </div>

        {/* 로고 워드마크 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 28,
            fontWeight: 700,
            color: PRIMARY,
            letterSpacing: "-0.02em",
          }}
        >
          jodalfit
        </div>

        {/* 메인 카피 */}
        <div style={{ display: "flex", flexDirection: "column", marginTop: 80, flex: 1 }}>
          <div
            style={{
              fontSize: 32,
              fontWeight: 500,
              color: PRIMARY,
              marginBottom: 24,
            }}
          >
            공공조달 입찰 디스커버리
          </div>
          <div
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: INK,
              lineHeight: 1.2,
              letterSpacing: "-0.03em",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div>우리 회사가 검토할 만한</div>
            <div>공공입찰을 골라드려요</div>
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 500,
              color: MUTED,
              marginTop: 32,
              lineHeight: 1.5,
            }}
          >
            등록업종 · 공급물품 · 수주 이력을 함께 분석해 TOP 5
          </div>
        </div>

        {/* 하단 메타 */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderTop: `1px solid ${BORDER}`,
            paddingTop: 24,
            fontSize: 22,
            color: MUTED,
            fontWeight: 500,
          }}
        >
          <div style={{ display: "flex" }}>나라장터 8개 OpenAPI · 매일 자동 갱신</div>
          <div style={{ display: "flex", color: PRIMARY, fontWeight: 700 }}>jodalfit.co.kr</div>
        </div>
      </div>
    ),
    { ...size, fonts: ogFonts(fonts) }
  );
}
