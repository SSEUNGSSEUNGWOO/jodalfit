// 검색 노출·AI 답변 인용과 무관한 수집 봇. robots.ts(disallow)와 proxy.ts(403)가 같은 목록을 쓴다.
// 왜 이 봇들인지는 robots.ts 주석. robots.txt 만으로는 안 멈춘다 — 차단 다음 날(2026-11-20)에도 ElevenlabsCrawler 295·
// Reflectionbot 116·ExaSearchBot 58·Bytespider 25·SemrushBot 15건이 회사 페이지 SSR(추천 API self-call)을 일으켰다.
export const BLOCKED_BOTS = [
  "AhrefsBot", "KeenableBot", "Keenable-SearchBot", "SERankingBacklinksBot", "AwarioBot", "ElevenlabsCrawler",
  "Bytespider", "Reflectionbot", "SemrushBot", "MJ12bot", "ConsultingCrawler", "ExaSearchBot", "meta-externalagent",
  "InterviewContactFinder", "OnseangRegistrationPublicPageVerifier",
];

const PATTERN = new RegExp(BLOCKED_BOTS.join("|"), "i");

export function isBlockedBot(userAgent: string | null): boolean {
  return !!userAgent && PATTERN.test(userAgent);
}
