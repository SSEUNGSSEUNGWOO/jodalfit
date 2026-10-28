const SID_KEY = "jf_sid";

/** 같은 탭의 검색·공고·가입 이동을 연결한다. 사용자 계정이나 이메일은 담지 않는다. */
export function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let sid = window.sessionStorage.getItem(SID_KEY);
    if (!sid) { sid = crypto.randomUUID(); window.sessionStorage.setItem(SID_KEY, sid); }
    return sid;
  } catch { return null; }
}
