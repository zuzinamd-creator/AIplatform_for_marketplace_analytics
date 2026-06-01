import React from "react";

import { cx } from "./cx";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
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
          "bg-sky-500/90 text-slate-50 hover:bg-sky-400 focus-visible:ring-2 focus-visible:ring-sky-300",
        variant === "secondary" &&
          "bg-slate-800 text-slate-50 hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-slate-400",
        variant === "ghost" && "bg-transparent text-slate-100 hover:bg-slate-800/60",
        variant === "danger" &&
          "bg-rose-500/90 text-white hover:bg-rose-400 focus-visible:ring-2 focus-visible:ring-rose-300",
        className,
      )}
      {...props}
    />
  );
}

