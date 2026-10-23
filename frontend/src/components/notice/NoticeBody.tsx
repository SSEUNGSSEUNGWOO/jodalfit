// frontend/src/components/notice/NoticeBody.tsx
// 공고 상세(07) 본문 — 과업 내용 · 필수/우대 조건 · 라이프사이클 단계 · 기관.
// 첨부문서 요약이 있으면 과업을 채우고, 없으면 왜 없는지와 첨부 원본으로 안내한다.
import type { LifecycleData } from "@/lib/lifecycle-data";
import type { BidNotice } from "@/lib/notice";
import type { NoticeInsight } from "@/types/recommendations";
import { cn } from "@/lib/utils";

const ymd = (s: string | null | undefined) => (s ? s.slice(0, 10).replace(/-/g, ".") : "—");

function Section({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <section className="mt-6 first:mt-0">
      <div className="flex flex-wrap items-baseline gap-x-3 border-b border-ink pb-2">
        <h2 className="text-[15px] font-[650] text-ink">{title}</h2>
        {sub && <span className="text-[12.5px] text-ink-g">{sub}</span>}
      </div>
      {children}
    </section>
  );
}

/** 과업 내용 — 첨부문서 요약(LLM)이 원천. 없으면 그 이유를 둘로 나눠 말한다. */
export function WorkSection({ n, insight }: { n: BidNotice; insight: NoticeInsight | null }) {
  const files = (n.attachments ?? []) as { seq?: number; name?: string; url: string }[];
  if (!insight?.summary) {
    // 기준은 파일 종류가 아니다(0058) — 경쟁입찰이고 마감이 안 지난 공고를 차례로 읽는다.
    // 수의계약은 앞으로도 안 읽는다. 기다리면 되는 것과 안 되는 것은 다르게 말해야 한다.
    const never = (n.cntrct_cncls_mthd_nm || "") === "수의계약";
    return (
      <Section title="과업 내용" sub="첨부 문서를 읽어 정리합니다">
        <p className="mt-3 text-[14px] leading-[1.8] text-ink-g">
          <b className="font-[650] text-ink">첨부문서를 아직 읽지 않았습니다.</b>{" "}
          {never
            ? "수의계약 공고는 문서를 읽지 않습니다 — 경쟁입찰만 분석합니다."
            : "순서를 기다리는 중입니다. 경쟁입찰 공고는 마감 전까지 차례로 읽습니다."}{" "}
          과업 내용·범위·필수 조건은 아래 첨부 원문에 있습니다.
        </p>
        {files.length > 0 && (
          <ul className="mt-2.5 text-[13.5px]">
            {files.slice(0, 8).map((f, i) => (
              <li key={f.url} className="border-b border-rule-2 py-1.5 last:border-0">
                <a href={f.url} className="break-all text-ink underline-offset-2 hover:text-orange hover:underline" rel="nofollow noopener">
                  {f.name || `첨부 ${f.seq ?? i + 1}`}
                </a>
              </li>
            ))}
          </ul>
        )}
      </Section>
    );
  }
  return (
    <Section title="과업 내용" sub="첨부 문서를 읽어 정리했습니다 · 원문 확인은 필수">
      <p className="mt-3 text-[14px] leading-[1.8] text-ink">{insight.summary}</p>
      {insight.scope && insight.scope.length > 0 && (
        <ul className="mt-3 list-disc pl-5 text-[14px] leading-[1.8] text-ink-g marker:text-ink-mute">
          {insight.scope.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
      {insight.keywords && insight.keywords.length > 0 && (
        <p className="mt-3 text-[12.5px] text-ink-g">
          <span className="text-ink-mute">문서에서 뽑은 말</span> {insight.keywords.slice(0, 8).join(" · ")}
        </p>
      )}
    </Section>
  );
}

const KIND_LABEL: Record<string, string> = {
  license: "면허·업종",
  certification: "인증",
  performance: "실적",
  region: "지역",
  company_size: "기업 규모",
  other: "기타",
};

export function RequirementsSection({ insight }: { insight: NoticeInsight | null }) {
  const reqs = insight?.requirements ?? [];
  if (!reqs.length) return null;
  const must = reqs.filter((r) => r.mandatory);
  const nice = reqs.filter((r) => !r.mandatory);
  return (
    <Section title="문서가 요구하는 조건" sub="조달핏이 자격으로 판정하지는 않습니다">
      {[
        { k: "필수", rows: must },
        { k: "우대", rows: nice },
      ]
        .filter((g) => g.rows.length)
        .map((g) => (
          <div key={g.k} className="mt-3">
            <span className="text-[12.5px] text-ink-g">{g.k} {g.rows.length}건</span>
            <ul className="mt-1.5">
              {g.rows.map((r, i) => (
                <li key={i} className="flex items-baseline gap-2.5 border-b border-rule-2 py-1.5 text-[13.5px] last:border-0">
                  <span className="w-[62px] shrink-0 text-[12px] text-ink-mute">{KIND_LABEL[r.kind] ?? r.kind}</span>
                  <span className={cn(g.k === "필수" ? "text-ink" : "text-ink-g")}>{r.text}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
    </Section>
  );
}

/** 라이프사이클 — 발주계획 → 사전규격 → 공고 → 마감 → 개찰 → 계약. 있는 단계만 적는다. */
export function StagesSection({ lc }: { lc: LifecycleData }) {
  const rows: { k: string; v: string; note?: string }[] = [];
  const plan = lc.orderPlans[0];
  if (plan?.order_year) rows.push({ k: "발주계획", v: `${plan.order_year}.${String(plan.order_mnth ?? "").padStart(2, "0")} 예정` });
  const spec = lc.preSpecs[0];
  if (spec) {
    rows.push({
      k: "사전규격",
      v: ymd(spec.rgst_dt),
      note: spec.opnin_rgst_clse_dt ? `의견 마감 ${ymd(spec.opnin_rgst_clse_dt)} · 의견 ${lc.opinionCount}건` : undefined,
    });
  }
  rows.push({ k: "입찰공고", v: ymd(lc.notice.bid_ntce_date) });
  rows.push({ k: "입찰 마감", v: ymd(lc.notice.bid_clse_date) });
  if (lc.awards.length) {
    const a = lc.awards[0];
    rows.push({ k: "개찰·낙찰", v: a.corp_nm || "—", note: a.bid_amt ? `${new Intl.NumberFormat("ko-KR").format(a.bid_amt)}원` : undefined });
  }
  if (lc.contracts.length) rows.push({ k: "계약", v: ymd(lc.contracts[0].cntrct_cncls_date) });

  return (
    <Section title="단계" sub="발주계획부터 계약까지 · 수집된 것만">
      <ul className="mt-2.5">
        {rows.map((r) => (
          <li key={r.k} className="grid grid-cols-[88px_minmax(0,1fr)] items-baseline gap-3 border-b border-rule py-2 text-[13.5px] last:border-0">
            <span className="text-ink-g">{r.k}</span>
            <span className="min-w-0">
              <span className="num text-ink">{r.v}</span>
              {r.note && <span className="ml-2 text-[12.5px] text-ink-g">{r.note}</span>}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function InstitutionSection({ n }: { n: BidNotice }) {
  const rows = [
    ["수요기관", n.dmnd_instt_nm],
    ["공고기관", n.ntce_instt_nm],
    ["업무 구분", n.bsns_div_nm],
    ["허용 업종", n.bidprc_psbl_indstryty_nm],
    ["참가 가능 지역", n.prtcpt_psbl_rgn_nm],
  ].filter(([, v]) => v) as [string, string][];
  if (!rows.length) return null;
  return (
    <Section title="기관·구분">
      <ul className="mt-2.5">
        {rows.map(([k, v]) => (
          <li key={k} className="grid grid-cols-[88px_minmax(0,1fr)] items-baseline gap-3 border-b border-rule py-2 text-[13.5px] last:border-0">
            <span className="text-ink-g">{k}</span>
            <span className="min-w-0 break-words text-ink">{v}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}
