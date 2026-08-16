import { ImageResponse } from "next/og";
import { loadPretendard, ogFonts } from "../../_og/fonts";
import { fetchBidNotice } from "@/lib/notice";
import { daysUntil, formatDateKR, formatKRW } from "@/lib/utils";

export const alt = "jodalfit 입찰공고";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PRIMARY = "#1e3a66";
const INK = "#111827";
const MUTED = "#6B7280";
const SURFACE = "#F7F9FC";
const BORDER = "#E5E7EB";
const WARN = "#F59E0B";
const DANGER = "#DC2626";

function truncate(s: string, max: number) {
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

function ddayColor(d: number | null) {
  if (d == null) return MUTED;
  if (d <= 2) return DANGER;
  if (d <= 5) return WARN;
  return PRIMARY;
}

export default async function Image({
  params,
}: {
  params: Promise<{ bid_ntce_no: string }>;
}) {
  const { bid_ntce_no } = await params;
  const fonts = await loadPretendard();

  const notice = await fetchBidNotice(bid_ntce_no).catch(() => null);

  const title = notice?.bid_ntce_nm ?? "입찰공고";
  const bsns = notice?.bsns_div_nm ?? null;
  const instt = notice?.dmnd_instt_nm ?? notice?.ntce_instt_nm ?? null;
  const price = notice?.presmpt_prce ?? notice?.asign_bdgt_amt ?? null;
  const closeDate = notice?.bid_clse_date ?? null;
  const d = daysUntil(closeDate);
  const ddayLabel =
    d == null ? null : d < 0 ? "마감" : d === 0 ? "D-Day" : `D-${d}`;

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
        {/* 상단: 워드마크 + 라이프사이클 라벨 */}
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
              gap: 8,
            }}
          >
            {bsns && (
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
                {bsns}
              </div>
            )}
            {ddayLabel && (
              <div
                style={{
                  display: "flex",
                  padding: "10px 20px",
                  background: ddayColor(d),
                  borderRadius: 999,
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#FFFFFF",
                }}
              >
                {ddayLabel}
              </div>
            )}
          </div>
        </div>

        {/* 메인 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            justifyContent: "center",
            marginTop: 40,
          }}
        >
          {/* 공고명 */}
          <div
            style={{
              fontSize: title.length > 40 ? 48 : title.length > 20 ? 60 : 72,
              fontWeight: 700,
              color: INK,
              lineHeight: 1.2,
              letterSpacing: "-0.03em",
              display: "flex",
            }}
          >
            {truncate(title, 60)}
          </div>

          {/* 기관 */}
          {instt && (
            <div
              style={{
                fontSize: 28,
                fontWeight: 500,
                color: MUTED,
                marginTop: 32,
                display: "flex",
              }}
            >
              {truncate(instt, 32)}
            </div>
          )}

          {/* 메타 row */}
          <div
            style={{
              display: "flex",
              gap: 40,
              marginTop: 36,
            }}
          >
            {price != null && (
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", fontSize: 18, color: MUTED, fontWeight: 500 }}>
                  추정가
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: 36,
                    fontWeight: 700,
                    color: INK,
                    marginTop: 4,
                  }}
                >
                  {formatKRW(price)}
                </div>
              </div>
            )}
            {closeDate && (
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", fontSize: 18, color: MUTED, fontWeight: 500 }}>
                  마감일
                </div>
                <div
                  style={{
                    display: "flex",
                    fontSize: 36,
                    fontWeight: 700,
                    color: INK,
                    marginTop: 4,
                  }}
                >
                  {formatDateKR(closeDate)}
                </div>
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", fontSize: 18, color: MUTED, fontWeight: 500 }}>
                공고번호
              </div>
              <div
                style={{
                  display: "flex",
                  fontSize: 30,
                  fontWeight: 700,
                  color: INK,
                  marginTop: 4,
                }}
              >
                {bid_ntce_no}
              </div>
            </div>
          </div>
        </div>

        {/* 하단 */}
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
          <div style={{ display: "flex" }}>
            발주계획 → 사전규격 → 공고 → 낙찰 → 계약 한눈에
          </div>
          <div style={{ display: "flex", color: PRIMARY, fontWeight: 700 }}>
            jodalfit.co.kr
          </div>
        </div>
      </div>
    ),
    { ...size, fonts: ogFonts(fonts) }
  );
}
