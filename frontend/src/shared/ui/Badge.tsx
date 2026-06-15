import type { ReactNode } from "react";

export type BadgeVariant = "success" | "danger" | "info" | "warn" | "accent";

export interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  pulse?: boolean;
  className?: string;
}

export function Badge({ children, variant = "info", pulse = false, className = "" }: BadgeProps) {
  return (
    <span className={`badge badge-${variant} ${pulse ? "badge-pulse" : ""} ${className}`.trim()}>
      <span className="badge-dot" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
