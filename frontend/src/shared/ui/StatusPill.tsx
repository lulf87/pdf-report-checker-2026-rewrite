import type { TaskModuleState } from "../../entities/task";

interface StatusPillProps {
  state: TaskModuleState;
  label: string;
}

export function StatusPill({ state, label }: StatusPillProps) {
  return <span className={`status-pill ${state}`}>{label}</span>;
}
