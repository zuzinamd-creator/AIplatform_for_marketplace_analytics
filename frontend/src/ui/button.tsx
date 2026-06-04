import React from "react";

import { cx } from "./cx";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "accent";
  size?: "sm" | "md" | "icon";
};

export function Button({ className, variant = "primary", size = "md", ...props }: Props) {
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" && "h-9 px-3 text-sm",
        size === "md" && "h-10 px-4 text-sm",
        size === "icon" && "h-9 w-9",
        variant === "primary" &&
          "bg-brand text-white shadow-sm hover:bg-brand-hover focus-visible:ring-2 focus-visible:ring-brand/40",
        variant === "secondary" &&
          "border border-surface-subtle bg-surface text-ink-secondary shadow-sm hover:bg-surface-inset focus-visible:ring-2 focus-visible:ring-brand/30",
        variant === "accent" &&
          "bg-semantic-success text-white shadow-sm hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500/40",
        variant === "ghost" && "bg-transparent text-ink-secondary hover:bg-surface-inset",
        variant === "danger" &&
          "bg-semantic-danger text-white shadow-sm hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500/40",
        className,
      )}
      {...props}
    />
  );
}
