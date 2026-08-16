import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function maskBizrno(bizrno: string | undefined | null) {
  if (!bizrno) return "—";
  const digits = bizrno.replace(/\D/g, "");
  if (digits.length !== 10) return bizrno;
  return `${digits.slice(0, 3)}-XX-X${digits.slice(7)}`;
}

export function formatKRW(value: number | null | undefined) {
  if (value == null) return "—";
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)}만`;
  // 나라장터 원천 데이터에 1원 등 placeholder 금액이 있어 미표기 처리
  return "—";
}

export function formatKRWFull(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString("ko-KR") + "원";
}

export function daysUntil(dateStr: string | null | undefined) {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  const ms = target.getTime() - today.getTime();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

export function formatDateKR(dateStr: string | null | undefined) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

export function scorePercent(score: number) {
  // 표시 스케일 재보정 (2026-08): raw 0~1을 √로 펴서 상위 추천이 체감
  // 점수대(75~95)에 오도록. 순위 보존 단조 변환 — "검토 우선순위" 표시용이며
  // 낙찰 확률이 아님(면책 문구 상시 병기). 임베딩 코사인 특성상 raw가
  // 0.5~0.8에 몰려 상위권도 60점대로 보이던 문제를 해소.
  const s = Math.max(0, Math.min(1, score));
  return Math.min(99, Math.round(Math.sqrt(s) * 100));
}

export function scoreLabel(score: number) {
  const p = scorePercent(score);
  if (p >= 90) return { label: "매우 적합", tone: "primary" as const };
  if (p >= 75) return { label: "적합", tone: "primary" as const };
  if (p >= 60) return { label: "관련 있음", tone: "muted" as const };
  return { label: "참고", tone: "muted" as const };
}
