import type { HTMLAttributes, ReactNode } from "react";

export interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  glow?: boolean;
}

export function GlassCard({ children, hover = false, glow = false, className = "", ...props }: GlassCardProps) {
  return (
    <div
      className={`glass-card ${hover ? "glass-card-hover" : ""} ${glow ? "glass-card-glow" : ""} ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
}
