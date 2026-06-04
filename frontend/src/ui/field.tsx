import React from "react";

import { cx } from "./cx";

export function Label(props: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} className={cx("text-xs font-medium text-ink-secondary", props.className)} />;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "h-10 w-full rounded-lg border border-surface-subtle bg-surface px-3 text-sm text-ink shadow-sm placeholder:text-ink-faint",
        "focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/25",
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
        "h-10 w-full rounded-lg border border-surface-subtle bg-surface px-3 text-sm text-ink shadow-sm",
        "focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/25",
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
        "w-full rounded-lg border border-surface-subtle bg-surface px-3 py-2.5 text-sm text-ink shadow-sm placeholder:text-ink-faint",
        "focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/25",
        props.className,
      )}
    />
  );
}
