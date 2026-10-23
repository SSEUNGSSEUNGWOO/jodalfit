// frontend/src/lib/supabase/browser.ts
"use client";

import { createBrowserClient } from "@supabase/ssr";

let client: ReturnType<typeof createBrowserClient> | null = null;

/** 클라이언트 컴포넌트 전용(anon 키). 쿠키에 세션을 쓰므로 서버(`lib/supabase/server.ts`)와 같은 세션을 본다. */
export function getBrowserSupabase() {
  if (!client) {
    client = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
  }
  return client;
}
