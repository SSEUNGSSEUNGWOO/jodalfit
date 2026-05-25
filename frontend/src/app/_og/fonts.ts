import "server-only";

const PRETENDARD_BOLD =
  "https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/public/static/Pretendard-Bold.otf";
const PRETENDARD_MEDIUM =
  "https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/public/static/Pretendard-Medium.otf";

let cached: { bold: ArrayBuffer; medium: ArrayBuffer } | null = null;

export async function loadPretendard() {
  if (cached) return cached;
  const [bold, medium] = await Promise.all([
    fetch(PRETENDARD_BOLD).then((r) => r.arrayBuffer()),
    fetch(PRETENDARD_MEDIUM).then((r) => r.arrayBuffer()),
  ]);
  cached = { bold, medium };
  return cached;
}

export function ogFonts(buffers: { bold: ArrayBuffer; medium: ArrayBuffer }) {
  return [
    { name: "Pretendard", data: buffers.medium, style: "normal" as const, weight: 500 as const },
    { name: "Pretendard", data: buffers.bold, style: "normal" as const, weight: 700 as const },
  ];
}
