// frontend/src/lib/changelog.ts
// 개선 기록(08) 의 원천은 docs/recommender/changelog.md 하나다 — 화면용 사본을 따로 두지 않는다.
// 사본을 두면 반드시 갈라진다(시안 숫자가 운영과 달랐던 2026-10-23 건과 같은 종류의 사고).
// 빌드 때 파일을 읽어 파싱한다. 문서가 바뀌면 다음 빌드에 반영된다.
import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";

export type ChangeEntry = {
  date: string | null; // YYYY-MM-DD, "지금" 항목은 null
  title: string;
  blocks: Block[];
  tag: "측정 전" | "처음 측정" | null;
};
export type Block =
  | { kind: "p"; toks: Tok[] }
  | { kind: "ul"; items: Tok[][] }
  | { kind: "table"; head: Tok[][]; rows: Tok[][][] };

/** 내부 작업 — 입찰 담당자에게 뜻이 없다. 원문에는 남기고 화면에서만 숨긴다(시안 gen_changelog.HIDE 와 같은 목록). */
const HIDE = [
  "재는 회사 수를 300곳에서 3,000곳으로",
  '"성공인데 0건"을 잡는 건강 점검',
  "프론트 검사 오류 4개 정리",
  "조건 검색에 키워드·발주기관을 더하는 바탕",
];
/** 채점표가 생긴 날. 그 전 항목은 전후 수치가 없어 '측정 전'. */
const MEASURED_FROM = "2026-10-13";

/** 글 한 토막. HTML 문자열을 만들지 않는다 — 화면은 React 요소로 그린다(dangerouslySetInnerHTML 없음). */
export type Tok = { t: string; b?: true; c?: true };

/** 굵게(**)·코드(`)만 해석한다. 나머지는 글자 그대로. */
function inline(s: string): Tok[] {
  const out: Tok[] = [];
  const re = /\*\*(.+?)\*\*|`(.+?)`/g;
  let last = 0;
  for (let m = re.exec(s); m; m = re.exec(s)) {
    if (m.index > last) out.push({ t: s.slice(last, m.index) });
    if (m[1] !== undefined) out.push({ t: m[1], b: true });
    else out.push({ t: m[2], c: true });
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push({ t: s.slice(last) });
  return out;
}

function parse(md: string): { lead: Tok[][]; entries: ChangeEntry[] } {
  const lines = md.split(/\r?\n/);
  const lead: Tok[][] = [];
  const entries: ChangeEntry[] = [];
  let cur: ChangeEntry | null = null;
  let buf: string[] = [];

  const flushPara = () => {
    const t = buf.join(" ").trim();
    buf = [];
    if (!t) return;
    if (cur) cur.blocks.push({ kind: "p", toks: inline(t) });
    else lead.push(inline(t));
  };

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    if (ln.startsWith("# ")) continue; // 문서 제목은 페이지가 따로 쓴다
    if (ln.startsWith("---")) {
      flushPara();
      continue;
    }
    if (ln.startsWith("## ")) {
      flushPara();
      const head = ln.slice(3).trim();
      const m = head.match(/^(\d{4}-\d{2}-\d{2})\s*·\s*(.+)$/);
      const date = m ? m[1] : null;
      const title = m ? m[2] : head;
      cur = {
        date,
        title,
        blocks: [],
        tag: !date ? null : date < MEASURED_FROM ? "측정 전" : title.startsWith("처음") ? "처음 측정" : null,
      };
      entries.push(cur);
      continue;
    }
    if (ln.startsWith("|")) {
      flushPara();
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        const cells = lines[i].slice(1, -1).split("|").map((c) => c.trim());
        if (!cells.every((c) => /^-+$/.test(c.replace(/:/g, "")))) rows.push(cells);
        i++;
      }
      i--;
      if (rows.length && cur) cur.blocks.push({ kind: "table", head: rows[0].map(inline), rows: rows.slice(1).map((r) => r.map(inline)) });
      continue;
    }
    if (/^[-*] /.test(ln)) {
      flushPara();
      const items: Tok[][] = [];
      while (i < lines.length && /^[-*] /.test(lines[i])) {
        items.push(inline(lines[i].replace(/^[-*] /, "")));
        i++;
      }
      i--;
      if (cur) cur.blocks.push({ kind: "ul", items });
      continue;
    }
    if (!ln.trim()) {
      flushPara();
      continue;
    }
    buf.push(ln.trim());
  }
  flushPara();
  return { lead, entries };
}

export type Changelog = {
  lead: Tok[][];
  now: ChangeEntry | null; // "지금" 항목 — 머리 숫자 판이 쓴다
  entries: ChangeEntry[]; // 최신순, HIDE 제외
  hidden: number;
  lastDate: string | null;
};

export async function getChangelog(): Promise<Changelog> {
  // 레포 안의 문서를 읽는다. 프론트 루트 기준 ../docs/…
  const file = path.join(process.cwd(), "..", "docs", "recommender", "changelog.md");
  const md = await readFile(file, "utf8");
  const { lead, entries } = parse(md);
  const now = entries.find((e) => !e.date && e.title.startsWith("지금")) ?? null;
  const dated = entries.filter((e) => e.date && !HIDE.includes(e.title));
  dated.sort((a, b) => (a.date! < b.date! ? 1 : a.date! > b.date! ? -1 : 0));
  return {
    lead,
    now,
    entries: dated,
    hidden: entries.filter((e) => e.date && HIDE.includes(e.title)).length,
    lastDate: dated[0]?.date ?? null,
  };
}
