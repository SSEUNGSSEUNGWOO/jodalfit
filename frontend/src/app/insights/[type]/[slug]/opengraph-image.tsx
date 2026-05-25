import { ImageResponse } from "next/og";
import { loadPretendard, ogFonts } from "../../../_og/fonts";
import { fetchInsight, type InsightType } from "@/lib/insights";

export const alt = "jodalfit 주간 인사이트";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PRIMARY = "#166534";
const INK = "#111827";
const MUTED = "#6B7280";
const SURFACE = "#F7F9FC";
const BORDER = "#E5E7EB";

function truncate(s: string, max: number) {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

function isType(t: string): t is InsightType {
  return t === "picks" || t === "market";
}

export default async function Image({
  params,
}: {
  params: Promise<{ type: string; slug: string }>;
}) {
  const { type, slug } = await params;
  const fonts = await loadPretendard();

  const insight = isType(type) ? await fetchInsight(type, slug).catch(() => null) : null;

  const title = insight?.meta.title ?? "주간 인사이트";
  const summary = insight?.meta.summary ?? "";
  const typeLabel = type === "picks" ? "이번 주 픽 · 검토할 만한 공고" : "이번 주 동향 · 시장 리포트";

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
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 28,
              fontWeight: 700,
              color: PRIMARY,
              letterSpacing: "-0.02em",
            }}
          >
            jodalfit
          </div>
          <div
            style={{
              display: "flex",
              padding: "10px 20px",
              background: SURFACE,
              border: `1px solid ${BORDER}`,
              borderRadius: 999,
              fontSize: 20,
              fontWeight: 700,
              color: INK,
            }}
          >
            {slug}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            justifyContent: "center",
            marginTop: 40,
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 26,
              fontWeight: 500,
              color: PRIMARY,
              marginBottom: 18,
            }}
          >
            {typeLabel}
          </div>
          <div
            style={{
              display: "flex",
              fontSize: title.length > 24 ? 56 : 64,
              fontWeight: 700,
              color: INK,
              lineHeight: 1.2,
              letterSpacing: "-0.03em",
            }}
          >
            {truncate(title, 40)}
          </div>
          {summary && (
            <div
              style={{
                display: "flex",
                fontSize: 22,
                fontWeight: 500,
                color: MUTED,
                marginTop: 28,
                lineHeight: 1.5,
              }}
            >
              {truncate(summary, 60)}
            </div>
          )}
        </div>

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
          <div style={{ display: "flex" }}>매주 월요일 발행 · jodalfit이 정리</div>
          <div style={{ display: "flex", color: PRIMARY, fontWeight: 700 }}>jodalfit.co.kr</div>
        </div>
      </div>
    ),
    { ...size, fonts: ogFonts(fonts) }
  );
}
