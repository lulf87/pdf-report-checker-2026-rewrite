# Shared Layouts

## App shell and route switch

- File: `frontend/src/app/App.tsx`
- Description: Root SPA shell. It normalizes the current hash route and renders the dashboard, report-check, or PTR-compare page inside `.app-shell`.
- Shared navigation/header/footer: No separate shared layout components currently exist; page headers and navigation are page-local.

```tsx
import { useEffect, useState } from "react";

import { DashboardPage } from "../features/dashboard/DashboardPage";
import { PTRComparePage } from "../features/ptr-compare/pages/PTRComparePage";
import { ReportCheckPage } from "../features/report-check/pages/ReportCheckPage";

export function App() {
  const [hash, setHash] = useState(() => window.location.hash || "#/");

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const path = hash.replace("#", "") || "/";

  return (
    <div className="app-shell">
      {path === "/ptr-compare" ? (
        <PTRComparePage />
      ) : path === "/report-check" ? (
        <ReportCheckPage />
      ) : (
        <DashboardPage />
      )}
    </div>
  );
}
```
