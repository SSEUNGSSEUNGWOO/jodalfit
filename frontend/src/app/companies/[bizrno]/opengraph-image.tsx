import { ImageResponse } from "next/og";
import { loadPretendard, ogFonts } from "../../_og/fonts";
import { fetchCompanyByBizrno } from "@/lib/company";
import { maskBizrno } from "@/lib/utils";

export const alt = "jodalfit 회사 분석";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PRIMARY = "#166534";
const INK = "#111827";
const MUTED = "#6B7280";
const SURFACE = "#F7F9FC";
const BORDER = "#E5E7EB";

function truncate(s: string, max: number) {
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

export default async function Image({
  params,
}: {
  params: Promise<{ bizrno: string }>;
}) {
  const { bizrno } = await params;
  const bizrnoNorm = bizrno.replace(/\D/g, "");
  const fonts = await loadPretendard();

  const company = bizrnoNorm.length === 10
    ? await fetchCompanyByBizrno(bizrnoNorm).catch(() => null)
    : null;

  const corpName = company?.corp_nm ?? "회사 분석";
  const region = company?.rgn_nm ?? null;
  const sector = company?.corp_bsns_div_nm ?? null;
  const manufacture = company?.mnfctr_div_nm ?? null;
  const masked = maskBizrno(bizrnoNorm);

  const metaChips = [region, sector, manufacture].filter(Boolean) as string[];

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
        {/* 상단 - 워드마크 + 라벨 */}
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
              fontWeight: 500,
              color: MUTED,
            }}
          >
            회사 영역 분석
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
          {/* 회사명 */}
          <div
            style={{
              fontSize: corpName.length > 18 ? 64 : 80,
              fontWeight: 700,
              color: INK,
              lineHeight: 1.15,
              letterSpacing: "-0.03em",
              display: "flex",
            }}
          >
            {truncate(corpName, 28)}
          </div>

          {/* 사업자번호 */}
          <div
            style={{
              fontSize: 26,
              fontWeight: 500,
              color: MUTED,
              marginTop: 24,
              display: "flex",
            }}
          >
            사업자번호 {masked}
          </div>

          {/* 메타 칩들 */}
          {metaChips.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: 12,
                marginTop: 40,
                flexWrap: "wrap",
              }}
            >
              {metaChips.map((chip, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    padding: "12px 24px",
                    background: i === 0 ? PRIMARY : SURFACE,
                    color: i === 0 ? "#FFFFFF" : INK,
                    border: i === 0 ? "none" : `1px solid ${BORDER}`,
                    borderRadius: 12,
                    fontSize: 24,
                    fontWeight: 500,
                  }}
                >
                  {truncate(chip, 24)}
                </div>
              ))}
            </div>
          )}
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
            이 회사에 맞는 입찰공고를 추천해드려요
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
