import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
}

// 서버 컴포넌트·route handler에서 난 에러
export const onRequestError = Sentry.captureRequestError;
