import * as Sentry from "@sentry/nextjs";

// DSN이 비어 있으면 SDK가 아무것도 보내지 않는다.
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0,
});
