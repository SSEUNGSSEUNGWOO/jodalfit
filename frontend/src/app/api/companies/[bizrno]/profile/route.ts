// frontend/src/app/api/companies/[bizrno]/profile/route.ts
// 결과 페이지 왼쪽 단 — 등록업종 목록·공급물품·수주 건수·사업자 상태. 공개 데이터, service_role 로 읽는다.
import { NextResponse } from "next/server";
import { fetchCompanyByBizrno, fetchCompanyProfile } from "@/lib/company";

export type CompanySideData = {
  industries: string[];      // 대표가 맨 앞
  repCount: number;          // 대표 업종 수(앞에서부터)
  products: string[];
  contractCount: number;
  status: string;            // "계속사업자" | "휴업" | "폐업" | "확인 전"
  restricted: boolean;
  checkedAt: string | null;  // YYYY-MM-DD
};

export async function GET(_: Request, { params }: { params: Promise<{ bizrno: string }> }) {
  const { bizrno } = await params;
  const norm = bizrno.replace(/\D/g, "");
  if (!/^\d{10}$/.test(norm)) return NextResponse.json({ error: "invalid bizrno" }, { status: 400 });
  const co = await fetchCompanyByBizrno(norm);
  if (!co) return NextResponse.json({ error: "not found" }, { status: 404 });
  // company_industries/company_supply_products.bizrno 는 하이픈 포함 원본 형식("124-81-77731")으로
  // 저장돼 있다(company.bizrno_norm 과 다름) — fetchCompanyProfile 은 co.bizrno 로 호출해야 매칭된다.
  const prof = await fetchCompanyProfile(co.bizrno);
  const status = co.biz_status_cd === "03" ? "폐업" : co.biz_status_cd === "02" ? "휴업" : co.biz_status_cd === "01" ? "계속사업자" : "확인 전";
  const body: CompanySideData = {
    industries: prof.industries,
    repCount: 1,
    products: prof.products,
    contractCount: co.contract_count ?? 0,
    status,
    restricted: !!co.is_restricted,
    checkedAt: (co.biz_status_checked_at ?? null)?.slice(0, 10) ?? null,
  };
  return NextResponse.json(body, { headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } });
}
