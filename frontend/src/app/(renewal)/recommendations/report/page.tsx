// frontend/src/app/(renewal)/recommendations/report/page.tsx
// 추천 공고 보고서 — A4 세로 한 장. 화면에선 종이색 위 210mm 판, 위에 "인쇄 / PDF 저장"만. 인쇄는 nav·footer 숨김(globals.css .report).
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Tile } from "@/components/Logo";
import { getRecommendations } from "@/lib/api";
import { getSessionUser } from "@/lib/auth";
import { dLeft, rgnBase, won } from "@/lib/format";
import { qualLines, whyLines } from "@/lib/why";
import { PrintButton } from "./PrintButton";

export const metadata: Metadata = { title: "추천 공고 보고서 | 조달핏", robots: { index: false, follow: false } };
const LABELS = ["지금 입찰 가능한 공고", "등록업종 허용 공고", "검토할 공고"];

export default async function ReportPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const p = await searchParams;
  const company = (p.company ?? "").trim();
  if (!company) redirect("/recommendations");
  const user = await getSessionUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(`/recommendations/report?company=${encodeURIComponent(company)}`)}`);
  const d = await getRecommendations({ query: company, mode: "company", limit: 12, candidate_pool: 200, with_explanation: false });
  if (!d.company) redirect(`/recommendations?company=${encodeURIComponent(company)}`);
  // Vercel 은 UTC — 기준일·D-day 는 KST 로
  const today = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Seoul" }));
  const ymd = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const f = d.funnel ?? null; const res = d.results;
  // 비스트림 응답은 자격 통과 수를 모른다 — 세 칸만(전체 → 업종 허용 → 검토할 공고). 캐시 히트로 funnel 자체가 없으면 띠를 안 그린다.
  const nums = [f?.total ?? null, f?.industry ?? null, res.length];
  return (
    <div className="report mx-auto w-[210mm] max-sm:w-auto">
      <div className="report-nav flex items-center justify-between py-[18px] pb-3 text-[13px] text-ink-g">
        <a href={`/recommendations?company=${encodeURIComponent(company)}`} className="border-b border-field text-ink">← 결과로 돌아가기</a>
        <PrintButton />
      </div>
      <div className="report-page flex min-h-[297mm] flex-col border border-hair bg-panel p-[16mm] text-[10px] leading-[1.3] text-ink">
        <div className="flex items-start justify-between border-b border-ink pb-2">
          <span className="flex items-center gap-1.5 text-[12px] font-extrabold tracking-[-0.035em]"><Tile size={20} />조달핏</span>
          <div className="text-right"><b>추천 공고 보고서 · 기준일 {ymd}</b><div className="mt-0.5 text-ink-g">{d.company.corp_nm} · {rgnBase(d.company.rgn_nm) || "—"}</div></div>
        </div>
        {f && (
          <div className="mt-2.5 flex items-start gap-3 border-b border-hair pb-2">
            <span className="t-k pt-0.5">걸러낸 경로</span>
            {nums.map((n, i) => (
              <div key={LABELS[i]} className="flex items-center gap-3"><div><b className={`num text-[13px] ${i === 2 ? "text-orange" : ""}`}>{n == null ? "—" : n.toLocaleString("ko-KR")}</b><div className="text-[9px] text-ink-mute">{LABELS[i]}</div></div>{i < 2 && <span className="text-ink-mute">→</span>}</div>
            ))}
          </div>
        )}
        <div className="t-k mt-3 border-b border-ink pb-1">검토할 공고 {res.length}건 · 적합 순</div>
        {res.map((b, i) => {
          const org = b.dmnd_instt_nm || b.ntce_instt_nm || "—"; const dl = dLeft(b.bid_clse_date, today);
          const q = qualLines(b.qualification).filter((l) => l.state !== "todo").map((l) => l.text.replace(" — ", " ") + (l.state === "ok" ? " ✓" : l.state === "warn" ? " !" : "")).join(" · ");
          return (
            <div key={`${b.bid_ntce_no}-${b.bid_ntce_ord}`} className="grid grid-cols-[20px_1fr] gap-x-1.5 border-b border-[#ececea] py-1 break-inside-avoid">
              <span className="num text-ink-mute">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <div className="flex items-baseline justify-between gap-3"><b className="text-[10.5px]">{b.bid_ntce_nm}</b>
                  <span className="num shrink-0">마감 <span className={dl && dl.days <= 7 ? "font-semibold text-orange" : "font-semibold"}>{dl ? `D-${dl.days}` : "—"}</span>{dl && ` (${dl.month}.${String(dl.day).padStart(2, "0")})`} · 추정가 {won(b.presmpt_prce)}</span></div>
                <div className="text-ink-g">{org}{b.bid_ntce_url && <> · <span className="text-ink-mute">{b.bid_ntce_url.replace("https://www.", "")}</span></>}</div>
                <div><span className="text-ink-mute">참가 자격</span> {q}</div>
                <div><span className="text-ink-mute">추천 근거</span> {whyLines(b.score_breakdown, org).slice(0, 2).join(" · ")}</div>
              </div>
            </div>
          );
        })}
        <div className="mt-auto flex items-center justify-between border-t border-ink pt-1.5 text-[9px] text-ink-g">
          <span><b className="text-ink">조달핏</b> · jodalfit.co.kr · 이 보고서는 낙찰 예측이 아니라 검토 대상 선별입니다 · 자격 판정은 나라장터 업체정보와 공고 제한 필드 기준이며 서류로 증빙되는 조건은 판정하지 않습니다</span>
          <span className="num">1 / 1</span>
        </div>
      </div>
    </div>
  );
}
