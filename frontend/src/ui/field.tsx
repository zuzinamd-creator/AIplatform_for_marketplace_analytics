import React from "react";

import { cx } from "./cx";

export function Label(props: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} className={cx("text-xs font-medium text-slate-200", props.className)} />;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "h-10 w-full rounded-lg border border-slate-800 bg-slate-950/40 px-3 text-sm text-slate-50 placeholder:text-slate-500",
        "focus-visible:border-sky-400 focus-visible:ring-2 focus-visible:ring-sky-500/30",
        props.className,
      )}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cx(
        "h-10 w-full rounded-lg border border-slate-800 bg-slate-950/40 px-3 text-sm text-slate-50",
        "focus-visible:border-sky-400 focus-visible:ring-2 focus-visible:ring-sky-500/30",
        props.className,
      )}
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cx(
        "w-full rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2 text-sm text-slate-50 placeholder:text-slate-500",
        "focus-visible:border-sky-400 focus-visible:ring-2 focus-visible:ring-sky-500/30",
        props.className,
      )}
    />
  );
}

