import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

// 보안 헤더(2026-10-26 보안 점검). Vercel 이 HSTS 는 붙이지만 나머지는 없었다.
// - frame-ancestors 'none': 로그인·비밀번호 변경 화면을 다른 사이트가 iframe 으로 씌우는 것(클릭재킹) 차단.
//   전체 CSP(script-src 등)는 PostHog·Sentry·Vercel 인라인 스크립트 때문에 nonce 작업이 필요해 뒤로 미룬다.
// - Referrer-Policy: 다른 사이트(나라장터 원문 링크 등)로 나갈 때 경로·검색어가 안 따라가게.
const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  // 주간 인사이트 콘텐츠 폐지(2026-10-15). 색인돼 있던 /insights 18개 URL 을
  // 홈으로 308 영구 리다이렉트 — 라우트를 그냥 지우면 soft 404 가 쌓인다.
  async redirects() {
    return [{ source: "/insights/:path*", destination: "/", permanent: true }];
  },
};

// org/project/SENTRY_AUTH_TOKEN이 없으면 소스맵 업로드만 건너뛴다. 에러 수집은 DSN만으로 된다.
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: !process.env.CI,
  widenClientFileUpload: true,
});
