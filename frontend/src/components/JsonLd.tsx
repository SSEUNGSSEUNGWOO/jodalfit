// frontend/src/components/JsonLd.tsx
// 구조화 데이터(JSON-LD) 한 조각. 검색엔진이 읽는다.
//
// 안전성: 내용은 **우리 DB 값으로 우리가 만든 객체**이고 사용자 입력을 그대로 싣지 않는다.
// serializeJsonLd 가 JSON.stringify 뒤 '<' 를 < 로 바꾼다 — `</script>` 로 빠져나가는
// 유일한 경로를 막는 표준 처리다. React 가 script 자식 텍스트를 이스케이프하면 JSON 이 깨지므로
// 이 자리에서는 원문 주입이 맞는 도구다. 쓰는 곳을 여기 하나로 모아 검토 지점을 한 곳으로 만든다.
import { serializeJsonLd, type Json } from "@/lib/jsonld";

export function JsonLd({ data }: { data: Json | Json[] }) {
  const html = { __html: serializeJsonLd(data) };
  return <script type="application/ld+json" {...{ dangerouslySetInnerHTML: html }} />;
}
