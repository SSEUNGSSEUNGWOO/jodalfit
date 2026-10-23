// frontend/src/components/Btn.tsx
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "dark" | "line" | "review" | "text";

const base = "inline-flex items-center justify-center h-9 px-3.5 rounded-[8px] text-[13px] font-semibold transition-colors duration-150 cursor-pointer select-none disabled:cursor-default";
const variants: Record<Variant, string> = {
  dark: "bg-ink text-white border border-ink hover:bg-[#2a2a2a] disabled:bg-field disabled:border-field disabled:text-ink-off",
  line: "bg-panel text-ink border border-field hover:border-orange",
  review: "bg-panel text-ink border border-orange data-[on=true]:text-ink-g data-[on=true]:border-field data-[on=true]:cursor-default",
  text: "h-auto px-1 text-ink-g font-medium border-0 [&>u]:no-underline [&>u]:border-b [&>u]:border-line hover:[&>u]:border-orange",
};

type Common = { variant?: Variant; className?: string; children: ReactNode; on?: boolean };
type AsLink = Common & { href: string } & Omit<ComponentProps<typeof Link>, "href" | "className" | "children">;
type AsButton = Common & { href?: undefined } & Omit<ComponentProps<"button">, "className" | "children">;

/** 링크면 <a>(Next Link), 아니면 <button>. shadcn Button 은 asChild 가 없어 링크에 못 쓴다. onClick 을 넘기는 쪽은 Client Component 여야 한다(서버 컴포넌트에서 핸들러를 넘기면 Next 가 거부). */
export function Btn(props: AsLink | AsButton) {
  const { variant = "line", className, children, on, ...rest } = props;
  const cls = cn(base, variants[variant], className);
  if ("href" in rest && rest.href) {
    const { href, ...a } = rest as AsLink;
    return <Link href={href} className={cls} data-on={on} {...a}>{children}</Link>;
  }
  const b = rest as AsButton;
  return <button type="button" className={cls} data-on={on} {...b}>{children}</button>;
}
