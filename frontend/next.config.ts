import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

const nextConfig: NextConfig = {
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
