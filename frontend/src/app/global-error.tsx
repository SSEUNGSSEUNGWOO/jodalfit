"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="ko">
      <body>
        <main style={{ padding: "4rem 1.5rem", textAlign: "center", fontFamily: "sans-serif" }}>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700 }}>일시적인 오류가 발생했어요</h1>
          <p style={{ marginTop: "0.75rem", color: "#6b7280" }}>잠시 후 새로고침해 주세요.</p>
        </main>
      </body>
    </html>
  );
}
