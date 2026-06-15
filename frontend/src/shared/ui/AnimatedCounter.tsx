import { useEffect, useState } from "react";

export interface AnimatedCounterProps {
  value: number;
  className?: string;
  formatValue?: (value: number) => string;
}

export function AnimatedCounter({
  value,
  className = "",
  formatValue = (item) => item.toString(),
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const startValue = displayValue;
    const delta = value - startValue;
    if (delta === 0) return;

    const startedAt = performance.now();
    const duration = 360;
    let frame = 0;

    const tick = (time: number) => {
      const progress = Math.min((time - startedAt) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(startValue + delta * eased));
      if (progress < 1) frame = window.requestAnimationFrame(tick);
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [value]);

  return <span className={`tabular ${className}`.trim()}>{formatValue(displayValue)}</span>;
}
