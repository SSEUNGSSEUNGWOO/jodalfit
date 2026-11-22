import { test } from "node:test";
import assert from "node:assert/strict";
import { isBlockedBot } from "./blocked-bots.ts";

test("차단 목록의 봇은 막는다", () => {
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; ElevenlabsCrawler/1.0; +https://elevenlabs.io/docs/bots)"), true);
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)"), true);
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; ExaSearchBot/1.0; +https://crawler.exa.ai/)"), true);
});

test("검색·AI 답변 봇과 사람은 통과시킨다", () => {
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; Yeti/1.1; +https://naver.me/spd)"), false);
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"), false);
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; ExaUser/1.0; +https://exauser.crawler.exa.ai)"), false);
  assert.equal(isBlockedBot("Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)"), false);
  assert.equal(isBlockedBot("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/157.0.0.0 Safari/537.36"), false);
  assert.equal(isBlockedBot(null), false);
});
