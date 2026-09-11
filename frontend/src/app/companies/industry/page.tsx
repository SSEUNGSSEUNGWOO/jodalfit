import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { fetchIndustryDirectory } from "@/lib/industry";

// 업종 목록은 하루 한 번 갱신되는 MV에서 읽는다.
export const revalidate = 86400;

export const metadata: Metadata = {
  title: "업종별 공공조달 기업 목록 | 조달핏",
  description:
    "나라장터 등록업종별로 공공조달 참여 기업을 찾아보세요. 토목·전기·정보통신·소프트웨어 등 업종을 선택하면 해당 업종으로 등록된 회사와 수주 이력을 볼 수 있습니다.",
  alternates: { canonical: "/companies/industry" },
};

export default async function IndustryDirectoryPage() {
  const industries = await fetchIndustryDirectory();

  return (
    <>
      <Header />
      <main className="world-gc flex-1">
        <section className="mx-auto max-w-[1080px] px-5 sm:px-8 pt-10 sm:pt-12 pb-16">
          <nav className="text-[12.5px] text-gc-ink-3" aria-label="브레드크럼">
            <Link href="/companies" className="hover:text-gc-ink font-semibold">
              공공조달 활동 기업
            </Link>
            <span className="mx-1.5">/</span>
            <span className="font-semibold text-gc-ink-2">업종별</span>
          </nav>

          <div className="gc-double-rule mt-3 pt-4 pb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h1 className="font-gc-serif font-black text-[24px] sm:text-[28px] tracking-[-0.02em] text-gc-ink break-keep">
              업종별 기업 목록
            </h1>
            <span className="text-[12.5px] text-gc-ink-3 tabular tabular-nums">
              {industries.length.toLocaleString("ko-KR")}개 업종
            </span>
          </div>

          <p className="mt-3 max-w-[64ch] text-[14px] leading-[1.65] text-gc-ink-2 break-keep">
            나라장터 등록업종 기준입니다. 한 회사가 여러 업종에 등록돼 있을 수 있으며, 조달핏이
            수주 이력을 분석한 회사만 셉니다.
          </p>

          <ol className="mt-6 border-t-2 border-gc-ink sm:columns-2 sm:gap-x-8">
            {industries.map((ind) => (
              <li key={ind.indstryty_cd} className="border-b border-gc-rule break-inside-avoid">
                <Link
                  href={`/companies/industry/${ind.indstryty_cd}/1`}
                  className="flex items-baseline justify-between gap-3 px-1 py-2.5 transition-colors hover:bg-gc-sheet"
                >
                  <span className="min-w-0 text-[14.5px] font-bold leading-[1.45] text-gc-ink break-keep">
                    {ind.indstryty_nm}
                  </span>
                  <span className="shrink-0 text-[12.5px] tabular tabular-nums text-gc-ink-3">
                    {ind.company_count.toLocaleString("ko-KR")}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      </main>
      <Footer className="mt-0" />
    </>
  );
}
