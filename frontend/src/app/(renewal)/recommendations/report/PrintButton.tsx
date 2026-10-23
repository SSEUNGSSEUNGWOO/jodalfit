"use client";
export function PrintButton() {
  return <button type="button" onClick={() => window.print()} className="cursor-pointer border-b-2 border-orange pb-px text-ink">인쇄 / PDF 저장</button>;
}
