import type { ReactNode } from "react";
import type { EvidenceStatus, PriorityLabel } from "../types";

export function Badge({
  children,
  variant,
}: {
  children: ReactNode;
  variant: PriorityLabel | EvidenceStatus | "neutral";
}) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      {label}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const message =
    error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="callout callout-danger" role="alert">
      {message}
    </div>
  );
}

export function Tags({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <span className="muted">—</span>;
  }
  return (
    <span>
      {items.map((item, i) => (
        <span className="tag" key={`${item}-${i}`}>
          {item}
        </span>
      ))}
    </span>
  );
}

export function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <span className="muted">None listed.</span>;
  }
  return (
    <ul className="list-plain">
      {items.map((item, i) => (
        <li key={`${item}-${i}`}>{item}</li>
      ))}
    </ul>
  );
}

/** Human-friendly label for a ranking component key. */
export function humanize(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (c) => c.toUpperCase())
    .trim();
}
