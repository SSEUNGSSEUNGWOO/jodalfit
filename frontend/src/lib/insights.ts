import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import matter from "gray-matter";

// gray-matter가 ISO date 문자열을 Date 객체로 자동 변환. React가 못 렌더하므로 string으로.
function normalizeMeta(data: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    out[k] = v instanceof Date ? v.toISOString().slice(0, 10) : v;
  }
  return out;
}

function parseFront(raw: string) {
  const m = matter(raw);
  return { content: m.content, data: normalizeMeta(m.data) };
}

const CONTENT_DIR = path.join(process.cwd(), "src", "content", "insights");

export type InsightType = "picks" | "market" | "guide";

export interface ChartDatum {
  label: string;
  value: number;
}

export interface InsightFrontmatter {
  title: string;
  summary: string;
  type: InsightType;
  slug: string;
  // weekly (picks/market) 전용 — guide는 이 필드 없음
  week_start?: string;
  week_end?: string;
  published_at: string;
  total_notices?: number;
  prev_total?: number;
  picks_count?: number;
  evaluation_score?: number;
  cover_image?: string;
  image_prompt?: string;
  chart_bsns?: ChartDatum[];
  chart_price?: ChartDatum[];
}

export interface Insight {
  type: InsightType;
  slug: string;
  body: string;
  meta: InsightFrontmatter;
}

export async function fetchInsight(
  type: InsightType,
  slug: string
): Promise<Insight | null> {
  const filePath = path.join(CONTENT_DIR, type, `${slug}.md`);
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    const parsed = parseFront(raw);
    const meta = parsed.data as unknown as InsightFrontmatter;
    return { type, slug, body: parsed.content, meta };
  } catch {
    return null;
  }
}

export interface InsightIndexItem {
  type: InsightType;
  slug: string;
  title: string;
  summary: string;
  week_start?: string;
  week_end?: string;
  published_at: string;
  evaluation_score?: number;
}

async function readAllOfType(type: InsightType): Promise<InsightIndexItem[]> {
  const dir = path.join(CONTENT_DIR, type);
  let files: string[];
  try {
    files = await fs.readdir(dir);
  } catch {
    return [];
  }
  const out: InsightIndexItem[] = [];
  for (const f of files) {
    if (!f.endsWith(".md")) continue;
    const slug = f.replace(/\.md$/, "");
    const raw = await fs.readFile(path.join(dir, f), "utf-8");
    const meta = parseFront(raw).data as unknown as InsightFrontmatter;
    out.push({
      type,
      slug,
      title: meta.title,
      summary: meta.summary,
      week_start: meta.week_start,
      week_end: meta.week_end,
      published_at: meta.published_at,
      evaluation_score: meta.evaluation_score,
    });
  }
  return out.sort((a, b) => (a.slug < b.slug ? 1 : -1));
}

export async function listAllInsights(): Promise<InsightIndexItem[]> {
  const [picks, market, guide] = await Promise.all([
    readAllOfType("picks"),
    readAllOfType("market"),
    readAllOfType("guide"),
  ]);
  return [...picks, ...market, ...guide].sort((a, b) => (a.slug < b.slug ? 1 : -1));
}

export async function listInsightsByType(
  type: InsightType
): Promise<InsightIndexItem[]> {
  return readAllOfType(type);
}
