import type { CSSProperties } from "react";

export const motionTiming = {
  fast: "140ms ease",
  normal: "220ms ease",
  slow: "360ms ease",
};

export const staggerStyle = (index: number): CSSProperties => ({
  animationDelay: `${Math.min(index * 45, 360)}ms`,
});
