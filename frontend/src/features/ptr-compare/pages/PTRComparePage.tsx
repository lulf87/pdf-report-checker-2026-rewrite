import { useState } from "react";

import type { TaskResult, TaskStatus } from "../../../entities/task/types";
import { PTRResults } from "../components/PTRResults";
import { PTRUpload } from "../components/PTRUpload";

export function PTRComparePage() {
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);

  function handleComplete(nextTask: TaskStatus, nextResult: TaskResult) {
    setTask(nextTask);
    setResult(nextResult);
  }

  function reset() {
    setTask(null);
    setResult(null);
  }

  return (
    <main className="page-shell">
      {task && result ? (
        <PTRResults
          onBack={() => (window.location.hash = "/")}
          onReupload={reset}
          result={result}
          task={task}
        />
      ) : (
        <PTRUpload onBack={() => (window.location.hash = "/")} onComplete={handleComplete} />
      )}
    </main>
  );
}
