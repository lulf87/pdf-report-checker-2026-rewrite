import { useState } from "react";

import type { TaskResult, TaskStatus } from "../../../entities/task/types";
import { clearTaskSession } from "../../../shared/lib/taskSessionStorage";
import { ReportResults } from "../components/ReportResults";
import { ReportUpload } from "../components/ReportUpload";

export function ReportCheckPage() {
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);

  function handleComplete(nextTask: TaskStatus, nextResult: TaskResult) {
    setTask(nextTask);
    setResult(nextResult);
  }

  function reset() {
    clearTaskSession("report_check");
    setTask(null);
    setResult(null);
  }

  return (
    <main className="page-shell">
      {task && result ? (
        <ReportResults
          onBack={() => (window.location.hash = "/")}
          onReupload={reset}
          result={result}
          task={task}
        />
      ) : (
        <ReportUpload onBack={() => (window.location.hash = "/")} onComplete={handleComplete} />
      )}
    </main>
  );
}
